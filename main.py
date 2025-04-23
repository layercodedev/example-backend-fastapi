import os
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator, Dict
import os
import asyncio
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()


# Message structure
class Message(BaseModel):
    role: str
    content: str
    id: Optional[str] = None


# Use a dictionary to store messages per session
session_messages: Dict[str, List[Message]] = {}

DEMO_DEFAULT_PROMPT = (
    "You are a helpful conversation assistant. You should respond to the user's message in a conversational manner. "
    "Your output will be spoken by a TTS model. You should respond in a way that is easy for the TTS model to speak and sound natural."
)


class RequestBody(BaseModel):
    text: str
    type: str
    session_id: str
    turn_id: str


GOOGLE_API_KEY = os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
print(f"GOOGLE_API_KEY: {GOOGLE_API_KEY}")
genai.configure(api_key=GOOGLE_API_KEY)

# Use a thread pool for blocking Gemini SDK calls
gemini_executor = ThreadPoolExecutor(max_workers=2)


# Helper to convert Pydantic messages to Gemini format
def to_gemini_messages(messages: List[Message]):
    return [{"role": m.role, "parts": [m.content]} for m in messages]


# Blocking function to get Gemini streaming response
def gemini_stream_response(messages: List[Message]):
    model = genai.GenerativeModel("gemini-2.0-flash-001")
    chat = model.start_chat(history=to_gemini_messages(messages[:-1]))
    return chat.send_message(messages[-1].content, stream=True)


# Async generator to yield Gemini response as SSE
async def stream_google_gemini(messages: List[Message]) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    # Run the blocking Gemini call in a thread pool
    stream = await loop.run_in_executor(
        gemini_executor, gemini_stream_response, messages
    )
    for chunk in stream:
        if hasattr(chunk, "text"):
            yield chunk.text
        elif isinstance(chunk, dict) and "text" in chunk:
            yield chunk["text"]


async def sse_event_generator(text_stream, turn_id, accumulate_response=False):
    full_response = ""
    async for chunk in text_stream:
        if accumulate_response:
            full_response += chunk
        data = json.dumps(
            {"type": "response.tts", "content": chunk, "turn_id": turn_id}
        )
        yield f"data: {data}\n\n"
    end_data = json.dumps({"type": "response.end", "turn_id": turn_id})
    yield f"data: {end_data}\n\n"


@app.post("/agent")
async def agent_endpoint(body: RequestBody):
    print(f"Received request: {body}")
    # Get or create the message list for this session
    messages = session_messages.setdefault(body.session_id, [])
    print(f"Messages: {messages}")
    if not messages:
        messages.append(Message(role="model", content=DEMO_DEFAULT_PROMPT))
    if body.type == "session.start":

        async def welcome_stream():
            data = json.dumps(
                {
                    "type": "response.tts",
                    "content": "Welcome to Layercode. How can I help you today?",
                    "turn_id": body.turn_id,
                }
            )
            yield f"data: {data}\n\n"
            end_data = json.dumps({"type": "response.end", "turn_id": body.turn_id})
            yield f"data: {end_data}\n\n"

        return StreamingResponse(welcome_stream(), media_type="text/event-stream")

    messages.append(Message(role="user", content=body.text))
    text_stream = stream_google_gemini(messages)

    async def streaming_and_save():
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
        messages.append(Message(role="model", content=full_response))

    return StreamingResponse(streaming_and_save(), media_type="text/event-stream")
