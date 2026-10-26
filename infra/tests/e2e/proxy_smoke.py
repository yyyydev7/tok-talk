#!/usr/bin/env python3
"""Check the release page, authentication and protected RAG routes through Nginx."""

import argparse
import json

from auth_checks import HttpClient, check_authentication, expect_status, origin_of


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8088")
    base = parser.parse_args().base.rstrip("/")
    client = HttpClient(base)
    status, body, _ = client.request("/")
    assert status == 200 and '<div id="app">' in body, "Release Vue page unavailable"
    print("PASS frontend: release Vue entry page available through proxy")
    status, body, _ = client.request("/health/live")
    assert status == 200 and json.loads(body).get("status") == "alive", "RAG liveness route failed"
    status, body, _ = client.request("/health")
    expect_status(status, 503, "RAG readiness through proxy")
    payload = json.loads(body)
    index_ready = payload.get("index_ready")
    assert isinstance(index_ready, bool), "Index readiness must be a boolean"
    assert payload.get("inventory_db_ready") is False, "Inventory DB is not implemented"
    print(f"PASS rag readiness: index_ready={index_ready}, inventory_db_ready=False")

    check_authentication(base, origin_of(base), rag_base=base, index_ready=index_ready)
    print("PASS rag: liveness, readiness, authentication and chemical list through proxy")
    print("Demo proxy checks passed. LLM answers are not exercised; inventory is not implemented.")
    print("One generated smoke account remains in this stack's database.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError) as error:
        raise SystemExit(f"FAIL: {error}") from error
