import base64
import hashlib
import hmac
import json
import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.chat import get_chat_service
from app.main import create_app
from app.services.chat import ChatConfigurationError, ChatProviderError, ChatService


def token(secret: str = "test-secret") -> str:
    def encode(value: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()

    payload = {
        "iss": "simple-auth-server",
        "aud": ["tok-talk-api"],
        "sub": "1",
        "iat": time.time() - 1,
        "exp": time.time() + 60,
        "jti": "chat-test",
    }
    signed = f"{encode({'alg': 'HS256', 'typ': 'JWT'})}.{encode(payload)}"
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signed.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{signed}.{signature}"


class FakeChatService:
    def answer(self, question: str) -> str:
        return f"답변: {question}"


class ChatApiTest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"JWT_SECRET": "test-secret"})
        self.env.start()
        self.app = create_app()
        self.app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
        self.client = TestClient(self.app)
        self.headers = {"Cookie": f"ACCESS_TOKEN={token()}"}

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def test_chat_requires_authentication(self):
        response = self.client.post("/chat-query", json={"question": "질문"})
        self.assertEqual(response.status_code, 401)

    def test_chat_returns_general_answer_shape(self):
        response = self.client.post(
            "/chat-query", headers=self.headers, json={"question": "오늘 날씨는?"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], "답변: 오늘 날씨는?")
        self.assertEqual(body["answer_mode"], "general")
        self.assertEqual(body["sources"], [])
        self.assertEqual(body["resolution"]["status"], "resolved")

    def test_chat_validates_question(self):
        for question in ("   ", "가" * 4001):
            with self.subTest(question_length=len(question)):
                response = self.client.post(
                    "/chat-query", headers=self.headers, json={"question": question}
                )
                self.assertEqual(response.status_code, 422)

    def test_chat_errors_do_not_expose_provider_details(self):
        class BrokenService:
            def answer(self, question: str) -> str:
                raise ChatProviderError("private provider response")

        self.app.dependency_overrides[get_chat_service] = lambda: BrokenService()
        response = self.client.post(
            "/chat-query", headers=self.headers, json={"question": "질문"}
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text)


class ChatServiceTest(unittest.TestCase):
    def test_service_uses_readable_answer(self):
        fake_llm = SimpleNamespace(
            invoke=lambda messages: SimpleNamespace(content=" 간결한 답변입니다. ")
        )
        self.assertEqual(ChatService(fake_llm).answer("질문"), "간결한 답변입니다.")

    def test_chemical_typo_uses_canonical_name_in_prompt_and_answer(self):
        prompts = []

        def invoke(messages):
            prompts.append(messages[-1][1])
            return SimpleNamespace(content="이세톤은 서늘한 곳에 보관하세요.")

        answer = ChatService(SimpleNamespace(invoke=invoke)).answer("이세톤 보관 방법")
        self.assertIn("질문: 아세톤 보관 방법", prompts[0])
        self.assertNotIn("이세톤", prompts[0])
        self.assertEqual(answer, "아세톤은 서늘한 곳에 보관하세요.")

    def test_unknown_name_is_not_guessed(self):
        prompts = []

        def invoke(messages):
            prompts.append(messages[-1][1])
            return SimpleNamespace(content="확인할 수 없습니다.")

        ChatService(SimpleNamespace(invoke=invoke)).answer("화학물질 보관 방법")
        self.assertEqual(prompts, ["화학물질 보관 방법"])

    def test_missing_key_is_a_configuration_error(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "", "OPENAI_API_KEY": ""}):
            with self.assertRaises(ChatConfigurationError):
                ChatService().answer("질문")


if __name__ == "__main__":
    unittest.main()
