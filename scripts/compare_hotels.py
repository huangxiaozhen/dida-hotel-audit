#!/usr/bin/env python3
"""Call the authenticated Dida audit gateway and print structured JSON."""

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
    parser = argparse.ArgumentParser(description="Compare two Dida hotel IDs")
    parser.add_argument("hotel_id_a", type=int)
    parser.add_argument("hotel_id_b", type=int)
    parser.add_argument("--language", default="en-US")
    args = parser.parse_args()
    if args.hotel_id_a <= 0 or args.hotel_id_b <= 0:
        parser.error("hotel IDs must be positive integers")
    try:
        result = call_gateway(
            "/v1/compare-hotels",
            {
                "hotel_id_a": args.hotel_id_a,
                "hotel_id_b": args.hotel_id_b,
                "language": args.language,
            },
        )
    except SecretStoreError as exc:
        result = {"ok": False, "error": {"code": "access_key_unavailable", "message": str(exc)}}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
