# Layercode Conversational AI Backend (FastAPI)

A lightweight Python service built with **FastAPI** that streams text-to-speech-ready replies from Google Gemini over Server-Sent Events (SSE). Each conversation is isolated by `session_id` so context is preserved across turns.

---

## ✨ Features

- **Session state** stored in memory – one history per user.
- **Real-time streaming** – incremental `response.tts` chunks delivered via SSE.
- **Google Gemini SDK** (official `google-generativeai`) integration.
- **Graceful fall-backs** – friendly responses on errors.

---

## 🚀 Quick Start

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

# Run (reload enabled for dev)
$ uvicorn main:app --reload --env-file .env
```

> Requires **Python 3.9+** and a valid **Gemini API key**.

---

## 🔧 Configuration

Add a `.env` file or export env-vars:

```env
GOOGLE_GENERATIVE_AI_API_KEY=your_api_key_here
PORT=8000   # Optional – FastAPI defaults to 8000
```

---

## 🗺️ API

### POST `/agent`

Send the user's text and receive streamed chunks.

#### Request JSON

```jsonc
{
  "text": "Hello, how are you?",
  "type": "message", // "message" or "session.start"
  "session_id": "sess-1234",
  "turn_id": "turn-0001"
}
```

#### Streaming Response (SSE)

```
data: {"type":"response.tts","content":"Hi there!","turn_id":"turn-0001"}

data: {"type":"response.end","turn_id":"turn-0001"}
```

| Type           | Description                         |
| -------------- | ----------------------------------- |
| `response.tts` | A partial or complete chunk of text |
| `response.end` | Indicates the turn has finished     |

---

## 🧩 Project Structure

| Path        | Purpose                           |
| ----------- | --------------------------------- |
| `main.py`   | Service implementation            |
| `README.md` | You are here                      |
| `.env`      | **Not committed** – local secrets |

---

## 🛠️ Dependencies

- `fastapi` / `uvicorn` – web framework & ASGI server
- `google-generativeai` – Gemini SDK
- `pydantic` – request / response models
- `python-dotenv` – load `.env` in development (optional)

All pinned in `requirements.txt` / `pyproject.toml`.

---

## 🩹 Troubleshooting

| Symptom                                | Fix                               |
| -------------------------------------- | --------------------------------- |
| `GOOGLE_GENERATIVE_AI_API_KEY not set` | Export var or add to `.env`       |
| Blocking I/O warnings                  | Ensure `uvicorn --reload` for dev |
| Empty or truncated response            | Check session consistency & logs  |

---

## 🔐 Security Notes

- Do **not** commit your `.env` / secrets.
- Use HTTPS & proper auth in production.
- Consider rate-limiting and persistence (e.g., Redis) for sessions.

---

## 📝 License

MIT – see [`LICENSE`](./LICENSE) for details.
