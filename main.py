import os
import json
import hmac
import hashlib
import time
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
import asyncio
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Webhook signature verification
def verify_signature(request_body: bytes, signature_header: str, secret: str, timestamp_tolerance: int = 300) -> bool:
    # signature_header is expected in the format: t=timestamp,v1=signature
    try:
        parts = dict(item.split('=') for item in signature_header.split(','))
        timestamp = int(parts['t'])
        signature = parts['v1']
    except Exception:
        return False

    # Check timestamp tolerance
    now = int(time.time())
    if abs(now - timestamp) > timestamp_tolerance:
        return False

    # Reconstruct signed payload
    signed_payload = f"{timestamp}.{request_body.decode()}"
    expected_signature = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

async def verify_webhook(request: Request):
    signature_header = request.headers.get("layercode-signature")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    body = await request.body()
    if not verify_signature(body, signature_header, os.getenv("LAYERCODE_WEBHOOK_SECRET", "")):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return body

class MessageContent(BaseModel):
    type: str
    text: str

class Message(BaseModel):
    role: str
    content: List[MessageContent]

session_messages: Dict[str, List[Message]] = {}

SYSTEM_PROMPT = (
    "You are a helpful conversation assistant. You should respond to the user's message in a conversational manner. "
    "Your output will be spoken by a TTS model. You should respond in a way that is easy for the TTS model to speak and sound natural."
)
WELCOME_MESSAGE = "Welcome to Layercode. How can I help you today?"

class RequestBody(BaseModel):
    text: str
    type: str
    session_id: str
    turn_id: str

GOOGLE_API_KEY = os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
gemini_executor = ThreadPoolExecutor(max_workers=2)

def to_gemini_messages(messages: List[Message]):
    # Flatten to Gemini's expected format
    return [
        {"role": m.role, "parts": [c.text for c in m.content if c.type == "text"]}
        for m in messages
    ]

def gemini_stream_response(messages: List[Message], system_prompt: str):
    model = genai.GenerativeModel("gemini-2.0-flash-001")
    # Copy messages to avoid mutating the original
    messages_for_gemini = messages.copy()
    if messages_for_gemini and messages_for_gemini[0].role == "user":
        # Prepend system prompt to the first user message
        messages_for_gemini[0].content[0].text = f"{system_prompt}\n\n{messages_for_gemini[0].content[0].text}"

    chat = model.start_chat(history=to_gemini_messages(messages_for_gemini))
    return chat.send_message(messages[-1].content[0].text, stream=True)

async def stream_google_gemini(messages: List[Message], system_prompt: str) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    stream = await loop.run_in_executor(
        gemini_executor, gemini_stream_response, messages, system_prompt
    )
    for chunk in stream:
        if hasattr(chunk, "text"):
            yield chunk.text
        elif isinstance(chunk, dict) and "text" in chunk:
            yield chunk["text"]

@app.post("/agent")
async def agent_endpoint(body: RequestBody, verified_body: bytes = Depends(verify_webhook)):
    messages = session_messages.setdefault(body.session_id, [])
    # Add user message
    messages.append(Message(role="user", content=[MessageContent(type="text", text=body.text)]))

    if body.type == "session.start":
        async def welcome_stream():
            data = json.dumps(
                {
                    "type": "response.tts",
                    "content": WELCOME_MESSAGE,
                    "turn_id": body.turn_id,
                }
            )
            yield f"data: {data}\n\n"
            messages.append(Message(role="assistant", content=[MessageContent(type="text", text=WELCOME_MESSAGE)]))
            session_messages[body.session_id] = messages
            end_data = json.dumps({"type": "response.end", "turn_id": body.turn_id})
            yield f"data: {end_data}\n\n"
        return StreamingResponse(welcome_stream(), media_type="text/event-stream")

    text_stream = stream_google_gemini(messages, SYSTEM_PROMPT)

    async def streaming_and_save():
        # Optionally send a data message (like in Next.js)
        data = json.dumps({"textToBeShown": "Hello, how can I help you today?"})
        yield f"data: {data}\n\n"

        full_response = ""
        async for chunk in text_stream:
            full_response += chunk
            data = json.dumps(
                {"type": "response.tts", "content": chunk, "turn_id": body.turn_id}
            )
            yield f"data: {data}\n\n"
        end_data = json.dumps({"type": "response.end", "turn_id": body.turn_id})
        yield f"data: {end_data}\n\n"
        # Save assistant's response to session
        messages.append(Message(role="assistant", content=[MessageContent(type="text", text=full_response)]))
        session_messages[body.session_id] = messages

    return StreamingResponse(streaming_and_save(), media_type="text/event-stream")
