from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import httpx
import json
import os

from system import SYSTEM_PROMPT

app = FastAPI()
templates = Jinja2Templates(directory="templates")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
WHOP_API_URL = "https://api.whop.com/api/v2/memberships/{license_key}/validate_license"
MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"

WHOP_API_KEY = os.environ.get("WHOP_API_KEY", "")
MASTER_KEY   = os.environ.get("MASTER_KEY", "")


# ── リクエストモデル ──────────────────────────────────────────

class ImageData(BaseModel):
    base64: str
    media_type: str

class Message(BaseModel):
    role: str
    content: str
    image: Optional[ImageData] = None

class ChatRequest(BaseModel):
    messages: list[Message]
    api_key: str
    license_key: str

class ValidateRequest(BaseModel):
    license_key: str


# ── ページ ───────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ── ライセンスキー検証 ────────────────────────────────────────

@app.post("/validate")
async def validate_license(req: ValidateRequest):
    if MASTER_KEY and req.license_key == MASTER_KEY:
        return JSONResponse({"valid": True})

    if not WHOP_API_KEY:
        raise HTTPException(status_code=500, detail="サーバー設定エラー: WHOP_API_KEYが未設定です")

    url = WHOP_API_URL.format(license_key=req.license_key)

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {WHOP_API_KEY}",
                "Content-Type": "application/json",
            },
            json={},
        )

    if response.status_code in (200, 201):
        return JSONResponse({"valid": True})
    else:
        return JSONResponse({"valid": False, "detail": "ライセンスキーが無効です"}, status_code=403)


# ── チャットAPI（SSEストリーミング） ──────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    if not WHOP_API_KEY:
        raise HTTPException(status_code=500, detail="サーバー設定エラー")

    if not (MASTER_KEY and req.license_key == MASTER_KEY):
        url = WHOP_API_URL.format(license_key=req.license_key)
        async with httpx.AsyncClient(timeout=10) as client:
            whop_res = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {WHOP_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={},
            )
        if whop_res.status_code not in (200, 201):
            raise HTTPException(status_code=403, detail="ライセンスキーが無効です")

    if not req.api_key.startswith("gsk_"):
        raise HTTPException(status_code=400, detail="Groq APIキーが正しくありません（gsk_ で始まる必要があります）")

    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for i, msg in enumerate(req.messages):
        is_last = i == len(req.messages) - 1

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
