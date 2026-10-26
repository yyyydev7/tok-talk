#!/usr/bin/env python3
"""Start/stop a temporary HTTPS tunnel without exposing a host port.

Uses the existing demo stack and its accounts. No credentials are copied or
printed. .env.public stores only the random public URL and hostname.
"""

import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".env.public"
PENDING = "https://pending.invalid"
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def saved_origin() -> str | None:
    if not STATE.exists():
        return None
    for line in STATE.read_text(encoding="utf-8").splitlines():
        if line.startswith("PUBLIC_ORIGIN="):
            origin = line.partition("=")[2]
            if URL_PATTERN.fullmatch(origin):
                return origin
    raise ValueError("Invalid .env.public; expected a trycloudflare.com HTTPS URL")


def compose(*args: str, public: bool = True, origin: str = PENDING,
            capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    command = ["docker", "compose", "--env-file", ".env.demo", "-f", "compose.demo.yaml"]
    if public:
        command.extend(["-f", "compose.public.yaml"])
    environment = os.environ.copy()
    environment["PUBLIC_ORIGIN"] = origin
    environment["PUBLIC_HOST"] = urlsplit(origin).hostname or "pending.invalid"
    return subprocess.run(command + list(args), cwd=ROOT, env=environment,
                          text=True, capture_output=capture, check=check, timeout=180)


def store_origin(origin: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ROOT,
                                     prefix=".env.public.", delete=False) as output:
        output.write(f"PUBLIC_ORIGIN={origin}\nPUBLIC_HOST={urlsplit(origin).hostname}\n")
        temporary = Path(output.name)
    try:
        os.replace(temporary, STATE)
    finally:
        temporary.unlink(missing_ok=True)


def restore_demo() -> None:
    # Close public ingress before changing the authentication settings.
    compose("stop", "tunnel")
    compose("rm", "--stop", "--force", "tunnel", "public-proxy")
    compose("up", "-d", "--no-deps", "--wait", "--wait-timeout", "90", "backend", public=False)
    # Nginx resolves backend's container address when it starts.
    compose("up", "-d", "--no-deps", "--force-recreate", "--wait",
            "--wait-timeout", "90", "proxy", public=False)
    STATE.unlink(missing_ok=True)


def wait_for_https(origin: str) -> None:
    print("Waiting for the public HTTPS page...", flush=True)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with urlopen(origin + "/", timeout=8) as response:
                if response.status == 200 and b'<div id="app">' in response.read(262144):
                    return
        except (OSError, ValueError):
            pass
        running = compose("ps", "--status", "running", "--services", capture=True)
        if "tunnel" not in running.stdout.splitlines():
            raise RuntimeError("The tunnel exited before HTTPS became available")
        time.sleep(2)
    raise RuntimeError("The public HTTPS page did not become available within 60 seconds")


def start() -> None:
    running = set(compose("ps", "--status", "running", "--services",
                          public=False, capture=True).stdout.splitlines())
    if not {"db", "backend", "rag", "frontend"}.issubset(running):
        raise ValueError("Start the demo first: docker compose --env-file .env.demo "
                         "-f compose.demo.yaml up --build -d --wait")

    existing = saved_origin()
    public_running = set(compose("ps", "--status", "running", "--services",
                                 capture=True).stdout.splitlines())
    if existing and "tunnel" in public_running:
        logs = compose("logs", "--no-color", "tunnel", capture=True).stdout
        urls = URL_PATTERN.findall(logs)
        if urls:
            # A manually restarted connector can keep old URLs in its logs.
            # Always configure the latest allocation rather than a saved one.
            current = urls[-1]
            try:
                store_origin(current)
                compose("up", "-d", "--no-deps", "--wait", "--wait-timeout", "90",
                        "backend", "public-proxy", origin=current)
                wait_for_https(current)
            except (Exception, KeyboardInterrupt):
                print("Public reconnection failed. Closing the tunnel and restoring the demo...", flush=True)
                restore_demo()
                raise
            print(f"Public demo is already running: {current}", flush=True)
            return

    compose("config", "--quiet")
    try:
        # An unknown Host is denied until the actual random URL is configured.
        print("Preparing the public gateway...", flush=True)
        compose("up", "-d", "--no-deps", "--wait", "--wait-timeout", "90", "public-proxy")
        print("Requesting a temporary HTTPS URL...", flush=True)
        compose("up", "-d", "--no-deps", "--force-recreate", "tunnel")
        deadline = time.monotonic() + 60
        origin = None
        while time.monotonic() < deadline:
            result = compose("logs", "--no-color", "tunnel", capture=True)
            match = URL_PATTERN.search(result.stdout + result.stderr)
            if match:
                origin = match.group(0)
                break
            time.sleep(1)
        if origin is None:
            raise RuntimeError("No tunnel URL received within 60 seconds; check Docker/network access")
        store_origin(origin)
        print("Applying HTTPS authentication and gateway settings...", flush=True)
        compose("up", "-d", "--no-deps", "--wait", "--wait-timeout", "90",
                "backend", "public-proxy", origin=origin)
        wait_for_https(origin)
    except (Exception, KeyboardInterrupt):
        print("Public startup did not finish. Closing the tunnel and restoring the demo...", flush=True)
        compose("logs", "--no-color", "--tail", "20", "public-proxy", check=False)
        restore_demo()
        raise
    print(f"Public demo: {origin}", flush=True)
    print("Keep this PC awake and Docker running. Sign in again at the HTTPS URL.", flush=True)
    print("Stop public access: python3 infra/scripts/public_demo.py stop", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"))
    action = parser.parse_args().action
    if not (ROOT / ".env.demo").exists():
        raise ValueError("Create .env.demo and start the demo stack first")
    if action == "start":
        start()
    elif action == "stop":
        restore_demo()
        print("Public access stopped. Local demo restored at the configured localhost port.")
    else:
        origin = saved_origin()
        print(f"Saved public demo URL: {origin}" if origin else "No public demo URL saved.")
        compose("ps", "--all", origin=origin or PENDING)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"FAIL: {error}") from error
