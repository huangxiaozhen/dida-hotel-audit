#!/usr/bin/env python3
"""Fetch one complete Dida static hotel record through the audit gateway."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dida_hotel_audit.gateway_client import call_gateway  # noqa: E402
from dida_hotel_audit.secrets_store import SecretStoreError  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Fetch one Dida hotel static record")
    parser.add_argument("hotel_id", type=int)
    parser.add_argument("--language", default="en-US")
    args = parser.parse_args()
    if args.hotel_id <= 0:
        parser.error("hotel ID must be a positive integer")
    try:
        result = call_gateway(
            "/v1/hotel-details",
            {"hotel_id": args.hotel_id, "language": args.language},
        )
    except SecretStoreError as exc:
        result = {
            "ok": False,
            "error": {"code": "access_key_unavailable", "message": str(exc)},
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
