#!/usr/bin/env python3
"""Create local development secrets without overwriting an existing .env."""

import argparse
import os
from pathlib import Path
import secrets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="create a separate .env.demo")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    destination = root / (".env.demo" if args.demo else ".env")
    template = (root / ".env.example").read_text(encoding="utf-8")
    replacements = {
        "DB_PASSWORD": secrets.token_hex(24),
        "DB_ROOT_PASSWORD": secrets.token_hex(24),
        "JWT_SECRET": secrets.token_hex(32),
    }
    if args.demo:
        replacements.update({
            "COMPOSE_PROJECT_NAME": "tok-talk-demo",
            "CORS_ORIGINS": "http://localhost:8088",
            "VITE_AUTH_BASE_URL": "",
            "VITE_RAG_BASE_URL": "",
        })
    lines = []
    for line in template.splitlines():
        key, separator, _ = line.partition("=")
        lines.append(f"{key}={replacements[key]}" if separator and key in replacements else line)
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f"Existing {destination.name} preserved.")
        return
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")
    print(f"Created private {destination.name}. Values are not printed.")


if __name__ == "__main__":
    main()
