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

from app.api.rag import _service
from app.main import create_app


def token(secret="test-secret", *, exp=None, iss="simple-auth-server"):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()

    signed = f"{encode({'alg': 'HS256', 'typ': 'JWT'})}.{encode({'iss': iss, 'sub': '1', 'exp': exp or time.time() + 60})}"
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signed.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{signed}.{signature}"


class FakeStore:
    index_to_docstore_id = {0: "acetone", 1: "methanol"}

    class docstore:
        @staticmethod
        def search(doc_id):
            return SimpleNamespace(metadata={"source": "NIOSH PDF", "cas_no": {
                "acetone": "67-64-1", "methanol": "67-56-1"}[doc_id]})


class FakeService:
    store = FakeStore()

    def answer(self, material_id, question, top_k):
        return {"answer": "근거 답변 [근거 1]", "sources": [], "needs_review": False,
                "material": {"material_id": material_id, "name": "아세톤",
                             "cas_number": "67-64-1"},
                "resolution": {"status": "resolved", "candidates": []}}


class RagApiTest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"JWT_SECRET": "test-secret",
                                        "JWT_ISSUER": "simple-auth-server",
                                        "CORS_ORIGINS": "http://localhost:5174"})
        self.env.start()
        self.app = create_app()
        self.app.dependency_overrides[_service] = lambda: FakeService()
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def auth(self, value=None):
        return {"Cookie": f"ACCESS_TOKEN={value or token()}"}

    def test_auth_and_cors(self):
        self.assertEqual(self.client.get("/chemicals").status_code, 401)
        self.assertEqual(self.client.get("/chemicals", headers=self.auth(token("wrong"))).status_code, 401)
        self.assertEqual(self.client.get("/chemicals", headers=self.auth(token(exp=1))).status_code, 401)
        response = self.client.options("/chemicals", headers={
            "Origin": "http://localhost:5174", "Access-Control-Request-Method": "GET"})
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5174")
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")

    def test_chemicals_and_question_flows(self):
        response = self.client.get("/chemicals?query=acetone", headers=self.auth())
        self.assertEqual([item["material_id"] for item in response.json()["items"]], ["acetone"])
        selected = self.client.post("/rag-query", headers=self.auth(), json={
            "material_id": "acetone", "question": "노출 경로는?"})
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json()["material"]["material_id"], "acetone")
        automatic = self.client.post("/rag-query/auto", headers=self.auth(), json={
            "question": "아세톤의 노출 경로는?"})
        self.assertEqual(automatic.json()["resolution"]["status"], "resolved")
        ambiguous = self.client.post("/rag-query/auto", headers=self.auth(), json={
            "question": "아세톤과 메탄올은?"})
        self.assertEqual(ambiguous.json()["resolution"]["status"], "ambiguous")
        missing = self.client.post("/rag-query/auto", headers=self.auth(), json={
            "question": "노출 경로는?"})
        self.assertEqual(missing.json()["resolution"]["status"], "not_found")

    def test_invalid_input(self):
        for body in ({"material_id": "unknown", "question": "질문"},
                     {"material_id": "acetone", "question": "   "},
                     {"material_id": "acetone", "question": "질문", "top_k": 11}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/rag-query", headers=self.auth(),
                                                  json=body).status_code, 422)


if __name__ == "__main__":
    unittest.main()
