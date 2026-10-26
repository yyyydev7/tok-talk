#!/usr/bin/env python3
"""Check the release page, authentication and protected RAG routes through Nginx."""

import argparse
import json
from urllib.parse import urlsplit

from auth_checks import HttpClient, check_authentication, expect_status, origin_of


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8088")
    parser.add_argument("--public", action="store_true", help="also require HTTPS, Secure cookies and Origin guards")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    if args.public and urlsplit(base).scheme != "https":
        raise ValueError("--public requires an HTTPS base URL")
    client = HttpClient(base)
    status, body, _ = client.request("/")
    assert status == 200 and '<div id="app">' in body, "Release Vue page unavailable"
    print("PASS frontend: release Vue entry page available through proxy")
    if args.public:
        for path in ("/login", "/ask", "/upgrade", "/materials"):
            status, body, _ = client.request(path)
            assert status == 200 and '<div id="app">' in body, f"SPA route unavailable: {path}"
        for origin in (None, "https://untrusted.invalid"):
            rejected = HttpClient(base, origin)
            for path in ("/api/login", "/chat-query", "/rag-query", "/rag-query/auto",
                         "/speech-to-text", "/text-to-speech"):
                status, _, _ = rejected.request(path, "POST")
                expect_status(status, 403, f"Public Origin guard: {path}")
        anonymous = HttpClient(base, origin_of(base))
        for path in ("/chat-query", "/speech-to-text", "/text-to-speech"):
            status, body, _ = anonymous.request(path, "POST")
            expect_status(status, 401, f"Anonymous AI request: {path}")
            assert json.loads(body).get("detail") == "UNAUTHORIZED", f"AI auth error missing: {path}"
        print("PASS public gateway: SPA routes work; missing and foreign POST Origins rejected")
        print("PASS public AI routes: chat, STT and TTS reach FastAPI and require authentication")
    status, body, _ = client.request("/health/live")
    assert status == 200 and json.loads(body).get("status") == "alive", "RAG liveness route failed"
    status, body, _ = client.request("/health")
    expect_status(status, 503, "RAG readiness through proxy")
    payload = json.loads(body)
    index_ready = payload.get("index_ready")
    assert isinstance(index_ready, bool), "Index readiness must be a boolean"
    if args.public:
        assert index_ready, "Public demo requires a ready RAG index"
    assert payload.get("inventory_db_ready") is False, "Inventory DB is not implemented"
    print(f"PASS rag readiness: index_ready={index_ready}, inventory_db_ready=False")

    check_authentication(base, origin_of(base), rag_base=base, index_ready=index_ready,
                         require_secure_cookie=args.public)
    print("PASS rag: liveness, readiness, authentication and chemical list through proxy")
    print("Public HTTPS checks passed." if args.public else "Demo proxy checks passed.")
    print("LLM answers are not exercised; inventory is not implemented.")
    print("One generated smoke account remains in this stack's database.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError) as error:
        raise SystemExit(f"FAIL: {error}") from error
