"""Deterministic distance calculation for hotel coordinate audits."""

from __future__ import annotations

from typing import Any

from .comparison import haversine_meters, summarize_hotel


def audit_hotel_coordinate(
    hotel: dict[str, Any],
    reference_latitude: float,
    reference_longitude: float,
    *,
    threshold_meters: float = 1000,
    reference_provider: str = "Google Maps",
    reference_name: str | None = None,
    reference_url: str | None = None,
) -> dict[str, Any]:
    if not -90 <= reference_latitude <= 90:
        raise ValueError("reference latitude must be between -90 and 90")
    if not -180 <= reference_longitude <= 180:
        raise ValueError("reference longitude must be between -180 and 180")
    if threshold_meters <= 0:
        raise ValueError("threshold_meters must be positive")

    summary = summarize_hotel(hotel)
    dida_coordinate = summary.get("coordinate")
    if not dida_coordinate:
        raise ValueError("The Dida hotel record does not contain a valid coordinate")
    distance = round(
        haversine_meters(
            dida_coordinate["latitude"],
            dida_coordinate["longitude"],
            reference_latitude,
            reference_longitude,
        ),
        2,
    )
    return {
        "dida": {
            "hotel_id": summary.get("id"),
            "name": summary.get("name"),
            "address": summary.get("address"),
            "telephone": summary.get("telephone"),
            "coordinate": dida_coordinate,
        },
        "reference": {
            "provider": reference_provider,
            "name": reference_name,
            "coordinate": {
                "latitude": reference_latitude,
                "longitude": reference_longitude,
            },
            "url": reference_url,
        },
        "distance_meters": distance,
        "threshold_meters": threshold_meters,
        "within_threshold": distance <= threshold_meters,
    }
