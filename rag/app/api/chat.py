"""Authenticated, index-independent question answering."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.security.jwt import verify_access_token
from app.services.chat import ChatConfigurationError, ChatProviderError, ChatService

router = APIRouter(tags=["chat"], dependencies=[Depends(verify_access_token)])


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)

    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("질문을 입력해 주세요.")
        return value.strip()


def get_chat_service() -> ChatService:
    return ChatService()


@router.post("/chat-query")
def chat_query(
    body: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> dict:
    try:
        answer = service.answer(body.question)
    except (ChatConfigurationError, ChatProviderError) as exc:
        raise HTTPException(
            status_code=503,
            detail="답변 생성 서비스를 사용할 수 없습니다.",
        ) from exc
    return {
        "answer": answer,
        "sources": [],
        "needs_review": True,
        "answer_mode": "general",
        "material": None,
        "resolution": {"status": "resolved", "candidates": []},
    }
