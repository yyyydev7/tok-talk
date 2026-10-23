"""Verify the Java server's HS256 ACCESS_TOKEN cookie."""

import base64
import binascii
import hashlib
import hmac
import json
import os
import time

from fastapi import Cookie, HTTPException, status


def _decode_part(part: str) -> dict:
    raw = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("JWT part must be an object")
    return value


def verify_access_token(access_token: str | None = Cookie(default=None, alias="ACCESS_TOKEN")) -> dict:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                 detail="UNAUTHORIZED")
    secret = os.getenv("JWT_SECRET", "")
    if not access_token or not secret:
        raise unauthorized
    try:
        header_part, payload_part, signature_part = access_token.split(".")
        header = _decode_part(header_part)
        payload = _decode_part(payload_part)
        if header.get("alg") != "HS256" or header.get("typ", "JWT") != "JWT":
            raise ValueError("Unexpected JWT algorithm")
        signed = f"{header_part}.{payload_part}".encode("ascii")
        expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
        signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        now = time.time()
        if payload.get("iss") != os.getenv("JWT_ISSUER", "simple-auth-server"):
            raise ValueError("Invalid issuer")
        if not isinstance(payload.get("exp"), (int, float)) or payload["exp"] <= now:
            raise ValueError("Expired token")
        if "nbf" in payload and (not isinstance(payload["nbf"], (int, float)) or payload["nbf"] > now):
            raise ValueError("Token not active")
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise ValueError("Missing subject")
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise unauthorized from None
    return payload
