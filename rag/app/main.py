"""FastAPI entry point for the Vue-facing RAG API."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.rag import router as rag_router
from app.api.speech import router as speech_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="톡talk API",
        version="0.3.0",
        description="KOSHA MSDS·NIOSH PDF 기반 물질 검색과 근거 답변 API",
    )
    origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5174").split(",")
               if item.strip() and item.strip() != "*"]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(health_router)
    application.include_router(chat_router)
    application.include_router(rag_router)
    application.include_router(speech_router)
    return application


app = create_app()
