#!/usr/bin/env python3
"""Check the release proxy without pretending business APIs are implemented."""

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(url: str, method: str = "GET") -> tuple[int, str]:
    query = Request(url, method=method)
    try:
        with urlopen(query, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8088")
    base = parser.parse_args().base.rstrip("/")
    status, body = request(base + "/")
    assert status == 200 and '<div id="app">' in body, "Release Vue page unavailable"
    status, body = request(base + "/health/live")
    assert status == 200 and json.loads(body).get("status") == "alive", "RAG liveness route failed"
    status, body = request(base + "/health")
    assert status == 503 and json.loads(body).get("index_ready") is False, "Readiness route failed"

    status, body = request(base + "/api/login", "POST")
    assert status == 404 and json.loads(body).get("error") == "not_found", "Java route not forwarded"
    for path, method in (("/chemicals", "GET"), ("/rag-query", "POST"),
                         ("/rag-query/auto", "POST"), ("/inventory", "GET")):
        status, body = request(base + path, method)
        assert status == 404 and json.loads(body).get("detail") == "Not Found", f"FastAPI route failed: {path}"
    print("PASS release Vue page, Java route, FastAPI routes, honest readiness through proxy")
    print("Business API 404 responses are expected until those APIs are implemented.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, URLError, ValueError) as error:
        raise SystemExit(f"FAIL: {error}") from error
