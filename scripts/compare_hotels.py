#!/usr/bin/env python3
"""Fetch and compare two Dida hotel records through the direct API client."""

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
    parser = argparse.ArgumentParser(description="Compare two Dida hotel IDs")
    parser.add_argument("hotel_id_a", type=int)
    parser.add_argument("hotel_id_b", type=int)
    parser.add_argument("--language", default="en-US")
    parser.add_argument(
        "--suspect-external-provider",
        action="append",
        default=[],
        help="exclude a provider such as giata from identity scoring while its mapping is audited",
    )
    args = parser.parse_args()
    if args.hotel_id_a <= 0 or args.hotel_id_b <= 0:
        parser.error("hotel IDs must be positive integers")
    try:
        result = HotelAuditService().compare_hotels(
            args.hotel_id_a,
            args.hotel_id_b,
            args.language,
            suspect_external_providers=args.suspect_external_provider,
        )
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
