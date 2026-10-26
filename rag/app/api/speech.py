"""Authenticated speech endpoints. Provider credentials never reach the browser."""

import os

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field, field_validator

from app.security.jwt import verify_access_token
from app.services.speech import (
    ElevenLabsSpeechService,
    SpeechConfigurationError,
    SpeechProviderError,
)

router = APIRouter(tags=["speech"], dependencies=[Depends(verify_access_token)])


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("읽을 텍스트를 입력해 주세요.")
        return value.strip()


def get_speech_service() -> ElevenLabsSpeechService:
    return ElevenLabsSpeechService()


def _provider_error(exc: Exception) -> HTTPException:
    status = 503 if isinstance(exc, SpeechConfigurationError) else 502
    return HTTPException(status_code=status, detail="음성 서비스를 사용할 수 없습니다.")


@router.post("/speech-to-text")
async def speech_to_text(
    file: UploadFile = File(...),
    service: ElevenLabsSpeechService = Depends(get_speech_service),
) -> dict[str, str]:
    content_type = (file.content_type or "application/octet-stream").split(";", 1)[0]
    if not (content_type.startswith("audio/") or content_type == "video/webm"):
        raise HTTPException(status_code=415, detail="지원하지 않는 음성 파일 형식입니다.")
    max_bytes = int(os.getenv("ELEVENLABS_MAX_AUDIO_BYTES", str(10 * 1024 * 1024)))
    try:
        audio = await file.read(max_bytes + 1)
    finally:
        await file.close()
    if not audio:
        raise HTTPException(status_code=422, detail="음성 파일이 비어 있습니다.")
    if len(audio) > max_bytes:
        raise HTTPException(status_code=413, detail="음성 파일이 너무 큽니다.")
    try:
        text = await service.transcribe(file.filename or "recording.webm", content_type, audio)
    except (SpeechConfigurationError, SpeechProviderError) as exc:
        raise _provider_error(exc) from exc
    return {"text": text}


@router.post("/text-to-speech", response_class=Response)
async def text_to_speech(
    body: SpeechRequest,
    service: ElevenLabsSpeechService = Depends(get_speech_service),
) -> Response:
    try:
        audio, content_type = await service.synthesize(body.text)
    except (SpeechConfigurationError, SpeechProviderError) as exc:
        raise _provider_error(exc) from exc
    return Response(
        content=audio,
        media_type=content_type,
        headers={"Cache-Control": "no-store", "Content-Disposition": "inline"},
    )
