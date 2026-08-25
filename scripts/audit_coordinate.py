#!/usr/bin/env python3
"""Compare one Dida coordinate with a verified external map coordinate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dida_hotel_audit.coordinate_audit import audit_hotel_coordinate  # noqa: E402
from dida_hotel_audit.credentials import CredentialError  # noqa: E402
from dida_hotel_audit.dida_client import DidaAPIError  # noqa: E402
from dida_hotel_audit.service import HotelAuditService  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description="Audit a Dida hotel coordinate against a verified map coordinate"
    )
    parser.add_argument("hotel_id", type=int)
    parser.add_argument("--reference-latitude", required=True, type=float)
    parser.add_argument("--reference-longitude", required=True, type=float)
    parser.add_argument("--reference-provider", default="Google Maps")
    parser.add_argument("--reference-name")
    parser.add_argument("--reference-url")
    parser.add_argument("--threshold-meters", type=float, default=1000)
    parser.add_argument("--language", default="en-US")
    args = parser.parse_args()
    if args.hotel_id <= 0:
        parser.error("hotel ID must be a positive integer")
    try:
        fetched = HotelAuditService().get_hotel(args.hotel_id, args.language)
        if not fetched.get("ok") or not isinstance(fetched.get("hotel"), dict):
            result = fetched
        else:
            audit = audit_hotel_coordinate(
                fetched["hotel"],
                args.reference_latitude,
                args.reference_longitude,
                threshold_meters=args.threshold_meters,
                reference_provider=args.reference_provider,
                reference_name=args.reference_name,
                reference_url=args.reference_url,
            )
            result = {
                "ok": True,
                "request": fetched.get("request"),
                "source": fetched.get("source"),
                "coordinate_audit": audit,
                "hotel": fetched["hotel"],
            }
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
    except ValueError as exc:
        result = {
            "ok": False,
            "error": {"code": "coordinate_audit_error", "message": str(exc)},
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
