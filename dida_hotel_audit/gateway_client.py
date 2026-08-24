"""Authenticated client for the configured Dida audit gateway."""

from __future__ import annotations

import json
from typing import Any
import urllib.error
import urllib.request

from .secrets_store import load_client_access


def call_gateway(path: str, payload: dict[str, Any], *, timeout: float = 45) -> dict[str, Any]:
    if not path.startswith("/v1/") or "://" in path:
        raise ValueError("Gateway path must be a /v1/ endpoint")
    gateway_url, access_key = load_client_access()
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        f"{gateway_url}{path}",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "dida-hotel-audit-skill/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {
                "ok": False,
                "error": {
                    "code": "gateway_http_error",
                    "message": f"Gateway returned HTTP {exc.code}",
                },
            }
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        return {
            "ok": False,
            "error": {
                "code": "gateway_unreachable",
                "message": f"Audit gateway is unreachable ({type(reason).__name__})",
            },
        }
