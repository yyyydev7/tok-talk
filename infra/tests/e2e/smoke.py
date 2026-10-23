#!/usr/bin/env python3
"""Smoke checks for the scaffold, not a completed product acceptance suite."""

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def request(url: str) -> tuple[int, str]:
    try:
        with urlopen(url, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", default="http://localhost:5174")
    parser.add_argument("--backend", default="http://localhost:8080")
    parser.add_argument("--rag", default="http://localhost:8001")
    args = parser.parse_args()

    status, body = request(args.frontend)
    assert status == 200 and '<div id="app">' in body, "Vue entry page unavailable"
    for name, base in (("backend", args.backend), ("rag", args.rag)):
        status, body = request(f"{base}/health/live")
        assert status == 200, f"{name} liveness failed: {status}"
        assert isinstance(json.loads(body), dict), f"{name} health is not JSON"
        status, body = request(f"{base}/health")
        assert status == 503, f"{name} must report unimplemented readiness as 503"
        payload = json.loads(body)
        if name == "backend":
            assert payload.get("auth_ready") is False, "Auth readiness must remain false"
        else:
            assert payload.get("index_ready") is False, "Index readiness must remain false"
            assert payload.get("inventory_db_ready") is False, "DB readiness must remain false"
        status, _ = request(f"{base}/not-a-route")
        assert status == 404, f"{name} must reject unknown routes"
        print(f"PASS {name}: alive, honest readiness, unknown route rejected")
    print("PASS frontend: Vue entry page available")
    print("Scaffold checks passed. Authentication, RAG and inventory are not implemented.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, URLError, ValueError) as error:
        raise SystemExit(f"FAIL: {error}") from error
