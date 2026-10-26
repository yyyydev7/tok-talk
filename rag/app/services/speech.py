"""Small, server-side ElevenLabs client for speech input and output."""

import os
from dataclasses import dataclass

import httpx


class SpeechConfigurationError(RuntimeError):
    """Raised when a required server-side setting is missing."""


class SpeechProviderError(RuntimeError):
    """Raised when ElevenLabs rejects or cannot complete a request."""


@dataclass(frozen=True)
class SpeechSettings:
    api_key: str
    voice_id: str
    tts_model: str
    stt_model: str
    stt_language: str
    output_format: str
    timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "SpeechSettings":
        return cls(
            api_key=os.getenv("ELEVENLABS_API_KEY", "").strip(),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "").strip(),
            tts_model=os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2").strip(),
            stt_model=os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2").strip(),
            stt_language=os.getenv("ELEVENLABS_STT_LANGUAGE", "kor").strip(),
            output_format=os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128").strip(),
            timeout_seconds=float(os.getenv("ELEVENLABS_TIMEOUT_SECONDS", "60")),
        )


class ElevenLabsSpeechService:
    base_url = "https://api.elevenlabs.io/v1"

    def __init__(self, settings: SpeechSettings | None = None):
        self.settings = settings or SpeechSettings.from_environment()

    def _headers(self) -> dict[str, str]:
        if not self.settings.api_key:
            raise SpeechConfigurationError("ELEVENLABS_API_KEY is not configured")
        return {"xi-api-key": self.settings.api_key}

    async def transcribe(self, filename: str, content_type: str, audio: bytes) -> str:
        form = {"model_id": self.settings.stt_model}
        if self.settings.stt_language:
            form["language_code"] = self.settings.stt_language
        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/speech-to-text",
                    headers=self._headers(),
                    data=form,
                    files={"file": (filename, audio, content_type)},
                )
            response.raise_for_status()
            text = response.json().get("text", "").strip()
        except SpeechConfigurationError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise SpeechProviderError("ElevenLabs speech-to-text failed") from exc
        if not text:
            raise SpeechProviderError("ElevenLabs returned an empty transcript")
        return text

    async def synthesize(self, text: str) -> tuple[bytes, str]:
        if not self.settings.voice_id:
            raise SpeechConfigurationError("ELEVENLABS_VOICE_ID is not configured")
        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{self.settings.voice_id}",
                    params={"output_format": self.settings.output_format},
                    headers={**self._headers(), "Accept": "audio/mpeg"},
                    json={"text": text, "model_id": self.settings.tts_model},
                )
            response.raise_for_status()
        except SpeechConfigurationError:
            raise
        except httpx.HTTPError as exc:
            raise SpeechProviderError("ElevenLabs text-to-speech failed") from exc
        if not response.content:
            raise SpeechProviderError("ElevenLabs returned empty audio")
        return response.content, response.headers.get("content-type", "audio/mpeg")
