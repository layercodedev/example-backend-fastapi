# Layercode Voice Agent Backend Example (FastAPI)

This open source project demonstrates how to build a real-time voice agent using [Layercode](https://layercode.com) Voice Pipelines, with a FastAPI backend to drive the agent's responses.

Read the companion guide: [FastAPI Backend Guide](https://docs.layercode.com/backend-guides/fastapi)

## Features

- **Browser or Phone Voice Interaction:** Users can speak to the agent directly from their browser or phone (see [Layercode docs](https://docs.layercode.com) for more details on connecting these channels)
- **Session State:** Conversation history is stored in memory. You can easily switch to a database or Redis to persist sessions.
- **LLM Integration:** User queries are sent to [Gemini Flash 2.0](https://ai.google.dev/gemini-api/docs/models/gemini).
- **Streaming Responses:** LLM responses are streamed back, where Layercode handles the conversion to speech and playback to the user.

## How It Works

1. **Frontend:**  
   See the [Layercode docs](https://docs.layercode.com) for details about connecting a Web Voice Agent frontend or Phone channel to the agent. This backend can also be tested our in the [Layercode Dashboard](https://dash.layercode.com) Playground

2. **Transcription & Webhook:**  
   Layercode transcribes user speech. For each complete message, it sends a webhook containing the transcribed text to the /agent endpoint.

3. **Backend Processing:**  
   The transcribed text is sent to the LLM (Gemini Flash 2.0) to generate a response.

4. **Streaming & Speech Synthesis:**  
   As soon as the LLM starts generating a response, the backend streams the output back as SSE messags to Layercode, which converts it to speech and delivers it to the frontend for playback in realtime.

## Getting Started

```bash
# Clone and enter the repo
$ git clone https://github.com/layercodedev/example-backend-fastapi.git && cd example-backend-fastapi

### With uv
# Installing uv
$ curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv & install deps
$ uv venv && source .venv/bin/activate
$ uv pip install -r requirements.txt

### With python
# Create venv & install deps (optional but recommended)
$ python -m venv .venv && source .venv/bin/activate
$ pip install -r requirements.txt
```

Edit your .env environment variables. You'll need to add:

- `GOOGLE_GENERATIVE_AI_API_KEY` - Your Google AI API key
- `LAYERCODE_WEBHOOK_SECRET` - Your Layercode pipeline's webhook secret, found in the [Layercode dashboard](https://dash.layercode.com) (goto your pipeline, click Edit in the Your Backend Box and copy the webhook secret shown)

If running locally, setup a tunnel (we recommend cloudflared which is free for dev) to your localhost so the Layercode webhook can reach your backend. Follow our tunneling guide here: [https://docs.layercode.com/tunnelling](https://docs.layercode.com/tunnelling)

If you didn't follow the tunneling guide, and are deploying this example to the internet, remember to set the Webhook URL in the [Layercode dashboard](https://dash.layercode.com/) (click Edit in the Your Backend box) to your publically accessible backend URL.

Now run the backend:

```bash
$ uvicorn main:app --reload --env-file .env --port 3000
```

The easiest way to talk to your agent is to use the [Layercode Dashboard](https://dash.layercode.com) Playground.

Tip: If you don't hear any response from your voice agent, check the Webhook Logs tab in your pipeline in the [Layercode Dashboard](https://dash.layercode.com/) to see the response from your backend.

## License

MIT
