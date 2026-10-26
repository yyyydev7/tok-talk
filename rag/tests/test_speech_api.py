import base64
import hashlib
import hmac
import json
import os
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.speech import get_speech_service
from app.main import create_app
from app.services.speech import SpeechConfigurationError, SpeechProviderError


def token(secret: str = "test-secret") -> str:
    def encode(value: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()

    payload = {
        "iss": "simple-auth-server",
        "aud": ["tok-talk-api"],
        "sub": "1",
        "iat": time.time() - 1,
        "exp": time.time() + 60,
        "jti": "speech-test",
    }
    signed = f"{encode({'alg': 'HS256', 'typ': 'JWT'})}.{encode(payload)}"
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signed.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{signed}.{signature}"


class FakeSpeechService:
    async def transcribe(self, filename: str, content_type: str, audio: bytes) -> str:
        return "아세톤의 노출 경로는 무엇인가요?"

    async def synthesize(self, text: str) -> tuple[bytes, str]:
        return b"fake-mp3", "audio/mpeg"


class SpeechApiTest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"JWT_SECRET": "test-secret"})
        self.env.start()
        self.app = create_app()
        self.app.dependency_overrides[get_speech_service] = lambda: FakeSpeechService()
        self.client = TestClient(self.app)
        self.headers = {"Cookie": f"ACCESS_TOKEN={token()}"}

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def test_speech_routes_require_authentication(self):
        self.assertEqual(
            self.client.post("/speech-to-text", files={"file": ("voice.webm", b"x", "audio/webm")}).status_code,
            401,
        )
        self.assertEqual(
            self.client.post("/text-to-speech", json={"text": "답변"}).status_code,
            401,
        )

    def test_transcribes_audio(self):
        response = self.client.post(
            "/speech-to-text",
            headers=self.headers,
            files={"file": ("voice.webm", b"audio", "audio/webm")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "아세톤의 노출 경로는 무엇인가요?")

    def test_rejects_empty_and_non_audio_files(self):
        empty = self.client.post(
            "/speech-to-text",
            headers=self.headers,
            files={"file": ("voice.webm", b"", "audio/webm")},
        )
        self.assertEqual(empty.status_code, 422)
        text = self.client.post(
            "/speech-to-text",
            headers=self.headers,
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        self.assertEqual(text.status_code, 415)

    def test_synthesizes_audio_without_caching(self):
        response = self.client.post(
            "/text-to-speech", headers=self.headers, json={"text": "안전 답변입니다."}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"fake-mp3")
        self.assertTrue(response.headers["content-type"].startswith("audio/mpeg"))
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_rejects_blank_or_oversized_text(self):
        self.assertEqual(
            self.client.post("/text-to-speech", headers=self.headers, json={"text": "   "}).status_code,
            422,
        )
        self.assertEqual(
            self.client.post("/text-to-speech", headers=self.headers, json={"text": "가" * 5001}).status_code,
            422,
        )

    def test_provider_errors_are_sanitized(self):
        class BrokenService(FakeSpeechService):
            async def synthesize(self, text: str) -> tuple[bytes, str]:
                raise SpeechProviderError("private provider details")

        self.app.dependency_overrides[get_speech_service] = lambda: BrokenService()
        response = self.client.post(
            "/text-to-speech", headers=self.headers, json={"text": "답변"}
        )
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private", response.text)

        class UnconfiguredService(FakeSpeechService):
            async def synthesize(self, text: str) -> tuple[bytes, str]:
                raise SpeechConfigurationError("secret env missing")

        self.app.dependency_overrides[get_speech_service] = lambda: UnconfiguredService()
        response = self.client.post(
            "/text-to-speech", headers=self.headers, json={"text": "답변"}
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.text)


if __name__ == "__main__":
    unittest.main()
