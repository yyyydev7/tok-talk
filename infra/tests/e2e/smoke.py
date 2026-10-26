#!/usr/bin/env python3
"""Check development services and the implemented authentication/RAG connection."""

import argparse
import json

from auth_checks import HttpClient, check_authentication, expect_status, origin_of


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", default="http://localhost:5174")
    parser.add_argument("--backend", default="http://localhost:8080")
    parser.add_argument("--rag", default="http://localhost:8001")
    args = parser.parse_args()

    status, body, _ = HttpClient(args.frontend).request("/")
    assert status == 200 and '<div id="app">' in body, "Vue entry page unavailable"
    print("PASS frontend: Vue entry page available")
    for name, base in (("backend", args.backend), ("rag", args.rag)):
        client = HttpClient(base)
        status, body, _ = client.request("/health/live")
        expect_status(status, 200, f"{name} liveness")
        assert json.loads(body).get("status") == "alive", f"{name} is not alive"
        status, body, _ = client.request("/health")
        expect_status(status, 200 if name == "backend" else 503, f"{name} readiness")
        payload = json.loads(body)
        if name == "backend":
            assert payload.get("auth_ready") is True, "Authentication must be ready"
        else:
            index_ready = payload.get("index_ready")
            assert isinstance(index_ready, bool), "Index readiness must be a boolean"
            assert payload.get("inventory_db_ready") is False, "Inventory DB is not implemented"
            print(f"PASS rag readiness: index_ready={index_ready}, inventory_db_ready=False")
        status, _, _ = client.request("/not-a-route")
        expect_status(status, 404, f"{name} unknown route")
        print(f"PASS {name}: liveness, readiness, unknown route")
    check_authentication(args.backend, origin_of(args.frontend),
                         rag_base=args.rag, index_ready=index_ready)
    print("Development checks passed. LLM answers are not exercised; inventory is not implemented.")
    print("One generated smoke account remains in this stack's database.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError) as error:
        raise SystemExit(f"FAIL: {error}") from error
