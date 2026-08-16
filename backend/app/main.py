from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import settings
from app.explain.ollama import check_ollama
from app.routes import chat, discover, documents, match
from app.schemas import HealthResponse, SessionSummary


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    yield


app = FastAPI(title="Resume Matcher", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(match.router)
app.include_router(chat.router)
app.include_router(discover.router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    ollama_ok = await check_ollama()
    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama_model=settings.ollama_model,
        embedding_model=settings.embedding_model,
        weights={
            "semantic": settings.semantic_weight,
            "keyword": settings.keyword_weight,
        },
    )


@app.get("/sessions", response_model=list[SessionSummary])
async def list_sessions() -> list[SessionSummary]:
    return [SessionSummary(**item) for item in db.list_sessions()]
