#!/usr/bin/env python3
"""Fetch complete Dida static records for one to fifty hotel IDs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dida_hotel_audit.credentials import CredentialError  # noqa: E402
from dida_hotel_audit.dida_client import DidaAPIError  # noqa: E402
from dida_hotel_audit.service import HotelAuditService  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description="Fetch complete Dida static hotel records for model analysis"
    )
    parser.add_argument("hotel_ids", type=int, nargs="+")
    parser.add_argument("--language", default="en-US")
    args = parser.parse_args()
    if len(args.hotel_ids) > 50:
        parser.error("at most 50 hotel IDs are allowed")
    if any(hotel_id <= 0 for hotel_id in args.hotel_ids):
        parser.error("hotel IDs must be positive integers")
    try:
        result = HotelAuditService().get_hotels(args.hotel_ids, args.language)
    except CredentialError as exc:
        result = {
            "ok": False,
            "error": {"code": "credentials_unavailable", "message": str(exc)},
        }
    except DidaAPIError as exc:
        result = {
            "ok": False,
            "error": {
                "code": "dida_api_error",
                "message": str(exc),
                "status": exc.status,
            },
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
