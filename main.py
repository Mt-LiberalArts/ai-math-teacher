from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import httpx
import json
import base64

from system import SYSTEM_PROMPT

app = FastAPI()
templates = Jinja2Templates(directory="templates")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


# ── リクエストモデル ──────────────────────────────────────────

class ImageData(BaseModel):
    base64: str
    media_type: str  # e.g. "image/jpeg"

class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str
    image: Optional[ImageData] = None  # 直近メッセージのみ使用

class ChatRequest(BaseModel):
    messages: list[Message]
    api_key: str


# ── ページ ───────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ── チャットAPI（SSEストリーミング） ──────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.api_key.startswith("gsk_"):
        raise HTTPException(status_code=400, detail="Groq APIキーが正しくありません（gsk_ で始まる必要があります）")

    # Groq用メッセージ構築
    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for i, msg in enumerate(req.messages):
        is_last = i == len(req.messages) - 1

        # 画像は最後のユーザーメッセージのみ送信（トークン節約）
        if msg.role == "user" and is_last and msg.image:
            groq_messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{msg.image.media_type};base64,{msg.image.base64}"
                        }
                    },
                    {"type": "text", "text": msg.content or "この問題を解説してください"}
                ]
            })
        else:
            groq_messages.append({"role": msg.role, "content": msg.content})

    payload = {
        "model": MODEL,
        "messages": groq_messages,
        "stream": True,
        "max_tokens": 2048,
        "temperature": 0.7,
    }

    async def event_generator():
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {req.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    error_msg = json.loads(body).get("error", {}).get("message", "Groq APIエラー")
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield f"data: {json.dumps({'content': delta})}\n\n"
                        except Exception:
                            continue

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
