"""Application service for fetching and comparing Dida hotel records."""

from __future__ import annotations

from typing import Any, Callable

from .comparison import compare_hotel_records
from .dida_client import DidaClient
from .secrets_store import get_dida_credentials


def _hotel_id(record: Any) -> int | None:
    if not isinstance(record, dict):
        return None
    lowered = {str(key).casefold(): value for key, value in record.items()}
    value = lowered.get("id", lowered.get("hotelid"))
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class HotelAuditService:
    def __init__(
        self,
        *,
        credentials_provider: Callable[[], tuple[str, str]] = get_dida_credentials,
        client_factory: Callable[[str, str], DidaClient] = DidaClient,
    ) -> None:
        self._credentials_provider = credentials_provider
        self._client_factory = client_factory

    def get_hotels(
        self, hotel_ids: list[int], language: str = "en-US"
    ) -> dict[str, Any]:
        if not isinstance(hotel_ids, list):
            raise ValueError("hotel_ids must be a list")
        if not hotel_ids:
            raise ValueError("hotel_ids must contain at least one ID")
        if len(hotel_ids) > 50:
            raise ValueError("hotel_ids cannot contain more than 50 IDs")
        if any(
            not isinstance(hotel_id, int)
            or isinstance(hotel_id, bool)
            or hotel_id <= 0
            for hotel_id in hotel_ids
        ):
            raise ValueError("Every hotel ID must be a positive integer")
        if not isinstance(language, str) or not language or len(language) > 16:
            raise ValueError("language must be a short language code")

        requested_ids = list(dict.fromkeys(hotel_ids))
        client_id, license_key = self._credentials_provider()
        client = self._client_factory(client_id, license_key)
        response = client.hotel_details(requested_ids, language)
        records = response.get("data")
        if not isinstance(records, list):
            records = []
        by_id = {
            _hotel_id(record): record
            for record in records
            if _hotel_id(record) is not None
        }
        ordered_records = [by_id[hotel_id] for hotel_id in requested_ids if hotel_id in by_id]
        missing_ids = [hotel_id for hotel_id in requested_ids if hotel_id not in by_id]
        return {
            "ok": not missing_ids,
            "request": {"hotel_ids": requested_ids, "language": language},
            "source": {
                "provider": "Dida Content API v2",
                "endpoint": "/api/v1/hotel/details",
                "trace_id": response.get("traceId"),
                "timestamp": response.get("timestamp"),
                "returned_record_count": len(ordered_records),
            },
            "missing_hotel_ids": missing_ids,
            "hotels": ordered_records,
        }

    def get_hotel(self, hotel_id: int, language: str = "en-US") -> dict[str, Any]:
        fetched = self.get_hotels([hotel_id], language)
        hotel = fetched["hotels"][0] if fetched["hotels"] else None
        return {
            "ok": hotel is not None,
            "request": {"hotel_id": hotel_id, "language": language},
            "source": fetched["source"],
            "hotel": hotel,
            "error": (
                None
                if hotel is not None
                else {
                    "code": "hotel_not_returned",
                    "message": "The requested Dida hotel record was not returned.",
                }
            ),
        }

    def compare_hotels(
        self, hotel_id_a: int, hotel_id_b: int, language: str = "en-US"
    ) -> dict[str, Any]:
        if not isinstance(hotel_id_a, int) or hotel_id_a <= 0:
            raise ValueError("hotel_id_a must be a positive integer")
        if not isinstance(hotel_id_b, int) or hotel_id_b <= 0:
            raise ValueError("hotel_id_b must be a positive integer")
        if not isinstance(language, str) or not language or len(language) > 16:
            raise ValueError("language must be a short language code")

        client_id, license_key = self._credentials_provider()
        client = self._client_factory(client_id, license_key)
        requested_ids = [hotel_id_a] if hotel_id_a == hotel_id_b else [hotel_id_a, hotel_id_b]
        response = client.hotel_details(requested_ids, language)
        records = response.get("data")
        if not isinstance(records, list):
            records = []
        by_id = {_hotel_id(record): record for record in records if _hotel_id(record) is not None}
        missing_ids = [hotel_id for hotel_id in requested_ids if hotel_id not in by_id]

        comparison: dict[str, Any]
        if missing_ids:
            comparison = {
                "decision": "insufficient_data",
                "confidence": "low",
                "reasons": ["One or more requested Dida hotel records were not returned."],
                "missing_hotel_ids": missing_ids,
                "evidence": [],
                "summaries": [],
            }
        elif hotel_id_a == hotel_id_b:
            comparison = compare_hotel_records(by_id[hotel_id_a], by_id[hotel_id_a])
        else:
            comparison = compare_hotel_records(by_id[hotel_id_a], by_id[hotel_id_b])

        return {
            "ok": not missing_ids,
            "request": {"hotel_ids": [hotel_id_a, hotel_id_b], "language": language},
            "source": {
                "provider": "Dida Content API v2",
                "endpoint": "/api/v1/hotel/details",
                "trace_id": response.get("traceId"),
                "timestamp": response.get("timestamp"),
                "returned_record_count": len(records),
            },
            "comparison": comparison,
            "hotels": records,
        }
