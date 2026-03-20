"""
main.py — FastAPI Backend
University of Layyah Chatbot API
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
from chatbot import get_chatbot, get_redis

# ── Lifespan (startup/shutdown) ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n🚀 Starting University of Layyah Chatbot API...")
    get_redis()
    get_chatbot()
    print("✅ API ready!\n")
    yield
    print("👋 Shutting down...")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="University of Layyah Chatbot API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ──────────────────────────────────────────────────
class HistoryMessage(BaseModel):
    """Single message in conversation history."""
    role: str       # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    """
    Chat request body.

    history: Previous conversation messages (max last 5 Q&A pairs = 10 messages).
             Frontend should maintain this list and grow it after each exchange:
               - After user sends: append {"role": "user", "content": question}
               - After bot replies: append {"role": "assistant", "content": answer}
             Send the FULL history list with each request.
             Backend automatically trims to last 5 Q&A pairs.
    """
    question: str
    history:  Optional[List[HistoryMessage]] = []

class ChatResponse(BaseModel):
    answer:    str
    cache_hit: bool = False

class ErrorResponse(BaseModel):
    error:        str
    rate_limited: bool = False


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(request: Request, body: ChatRequest):
    """
    Main chat endpoint.

    Frontend usage:
        POST /api/chat
        {
            "question": "BSCS ki fees kya hain?",
            "history": [
                {"role": "user",      "content": "Admissions kab hoti hain?"},
                {"role": "assistant", "content": "Admissions usually July-August mein hoti hain..."}
            ]
        }
    """
    ip      = request.client.host if request.client else "0.0.0.0"
    chatbot = get_chatbot()

    # Convert pydantic models to plain dicts for chatbot
    history_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in (body.history or [])
    ]

    result = chatbot.ask(
        question = body.question,
        ip       = ip,
        history  = history_dicts
    )

    if "error" in result:
        from fastapi.responses import JSONResponse
        status = 429 if result.get("rate_limited") else 500
        return JSONResponse(status_code=status, content=result)

    return {
        "answer":    result["answer"],
        "cache_hit": result.get("cache_hit", False)
    }


@app.get("/api/health")
async def health():
    """Health check."""
    try:
        chatbot    = get_chatbot()
        collection = chatbot.embedder  # just check it's loaded
        redis_ok   = get_redis() is not None
        return {
            "status":    "ok",
            "redis":     "connected" if redis_ok else "unavailable",
            "chromadb":  "connected",
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/stats")
async def stats():
    """Collection stats."""
    try:
        from chatbot import get_collection
        col = get_collection()
        return {
            "chunks_indexed": col.count(),
            "collection":     col.name,
        }
    except Exception as e:
        return {"error": str(e)}