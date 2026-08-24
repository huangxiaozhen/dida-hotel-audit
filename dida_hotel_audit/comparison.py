"""Deterministic evidence extraction for Dida hotel identity comparison."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import math
import re
import unicodedata
from typing import Any, Iterable


_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)
_GENERIC_HOTEL_NAME_WORDS = {
    "hotel",
    "hotels",
    "hostel",
    "inn",
    "motel",
    "resort",
    "the",
}


def _case_get(value: Any, *names: str) -> Any:
    if not isinstance(value, dict):
        return None
    lowered = {str(key).casefold(): item for key, item in value.items()}
    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]
    return None


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold().replace("&", " and ")
    return " ".join(_NON_WORD.sub(" ", text).split())


def normalize_phone(value: Any) -> str:
    if value is None:
        return ""
    digits = "".join(character for character in str(value) if character.isdigit())
    return digits[2:] if digits.startswith("00") else digits


def similarity(left: Any, right: Any) -> float | None:
    a = normalize_text(left)
    b = normalize_text(right)
    if not a or not b:
        return None
    return round(SequenceMatcher(None, a, b).ratio(), 4)


def hotel_name_similarity(left: Any, right: Any) -> float | None:
    """Compare names while tolerating token order and location suffixes."""
    base = similarity(left, right)
    if base is None:
        return None
    left_tokens = set(normalize_text(left).split()) - _GENERIC_HOTEL_NAME_WORDS
    right_tokens = set(normalize_text(right).split()) - _GENERIC_HOTEL_NAME_WORDS
    if not left_tokens or not right_tokens:
        return base
    if left_tokens == right_tokens:
        return 1.0
    overlap = left_tokens & right_tokens
    if len(overlap) < 2:
        return base
    containment = len(overlap) / min(len(left_tokens), len(right_tokens))
    return round(max(base, containment), 4)


def haversine_meters(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    radius = 6_371_008.8
    phi_a = math.radians(latitude_a)
    phi_b = math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coordinate(record: dict[str, Any]) -> tuple[float, float] | None:
    location = _case_get(record, "location") or {}
    coordinate = _first(
        _case_get(location, "coordinate", "coordinates"),
        _case_get(record, "coordinate", "coordinates"),
    ) or {}
    latitude = _first(
        _case_get(coordinate, "latitude", "lat"),
        _case_get(location, "latitude", "lat"),
        _case_get(record, "latitude", "lat"),
    )
    longitude = _first(
        _case_get(coordinate, "longitude", "lng", "lon"),
        _case_get(location, "longitude", "lng", "lon"),
        _case_get(record, "longitude", "lng", "lon"),
    )
    lat = _as_float(latitude)
    lon = _as_float(longitude)
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return None
    return lat, lon


def _code_name(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "code": _case_get(value, "code", "id"),
            "name": _case_get(value, "name"),
        }
    return {"code": value, "name": None}


def _recursive_pairs(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, (dict, list)):
                yield from _recursive_pairs(item, path)
            else:
                yield path, item
    elif isinstance(value, list):
        for index, item in enumerate(value):
            path = f"{prefix}[{index}]"
            if isinstance(item, (dict, list)):
                yield from _recursive_pairs(item, path)
            else:
                yield path, item


def _external_ids(record: dict[str, Any]) -> dict[str, list[str]]:
    identifiers: dict[str, set[str]] = {}
    allowed_fragments = ("giata", "vervotech", "hotelbeds", "expedia", "ean")
    for path, value in _recursive_pairs(record):
        path_key = path.casefold()
        if value in (None, "") or not any(fragment in path_key for fragment in allowed_fragments):
            continue
        leaf = path.split(".")[-1].split("[")[0].casefold()
        key = next((fragment for fragment in allowed_fragments if fragment in path_key), leaf)
        identifiers.setdefault(key, set()).add(str(value).strip())
    return {key: sorted(values) for key, values in sorted(identifiers.items())}


def _room_count(record: dict[str, Any]) -> Any:
    direct = _case_get(record, "roomCount", "numberOfRooms", "totalRooms")
    if direct is not None:
        return direct
    rooms = _case_get(record, "rooms", "roomTypes", "roomInfo")
    return len(rooms) if isinstance(rooms, list) else None


def summarize_hotel(record: dict[str, Any]) -> dict[str, Any]:
    location = _case_get(record, "location") or {}
    coordinate = _coordinate(record)
    return {
        "id": _first(_case_get(record, "id"), _case_get(record, "hotelId", "hotelID")),
        "name": _first(_case_get(record, "name"), _case_get(record, "hotelName")),
        "address": _first(_case_get(location, "address"), _case_get(record, "address")),
        "coordinate": (
            {"latitude": coordinate[0], "longitude": coordinate[1]} if coordinate else None
        ),
        "telephone": _first(
            _case_get(record, "telephone", "phone", "phoneNumber"),
            _case_get(location, "telephone", "phone"),
        ),
        "zip_code": _first(
            _case_get(record, "zipCode", "postalCode"),
            _case_get(location, "zipCode", "postalCode"),
        ),
        "star_rating": _case_get(record, "starRating", "stars"),
        "country": _code_name(_case_get(location, "country")),
        "destination": _code_name(_case_get(location, "destination")),
        "city": _code_name(_case_get(location, "city")),
        "external_identifiers": _external_ids(record),
        "room_count": _room_count(record),
    }


@dataclass
class _Score:
    positive: int = 0
    negative: int = 0


def _value_state(left: Any, right: Any, *, normalizer=normalize_text) -> str:
    a = normalizer(left)
    b = normalizer(right)
    if not a or not b:
        return "missing"
    return "match" if a == b else "conflict"


def compare_hotel_records(
    record_a: dict[str, Any], record_b: dict[str, Any]
) -> dict[str, Any]:
    left = summarize_hotel(record_a)
    right = summarize_hotel(record_b)
    score = _Score()
    evidence: list[dict[str, Any]] = []
    reasons: list[str] = []

    id_a = left["id"]
    id_b = right["id"]
    if id_a is not None and str(id_a) == str(id_b):
        return {
            "decision": "same_hotel",
            "confidence": "high",
            "score": {"positive": 99, "negative": 0},
            "reasons": ["The two records have the same Dida hotel ID."],
            "evidence": [{"field": "dida_id", "left": id_a, "right": id_b, "state": "match"}],
            "summaries": [left, right],
        }

    name_similarity = hotel_name_similarity(left["name"], right["name"])
    name_state = "missing" if name_similarity is None else (
        "strong_match" if name_similarity >= 0.9 else "similar" if name_similarity >= 0.7 else "conflict"
    )
    evidence.append(
        {
            "field": "name",
            "left": left["name"],
            "right": right["name"],
            "state": name_state,
            "similarity": name_similarity,
        }
    )
    if name_similarity is not None:
        if name_similarity >= 0.9:
            score.positive += 3
        elif name_similarity >= 0.7:
            score.positive += 2
        elif name_similarity >= 0.5:
            score.positive += 1
        elif name_similarity < 0.35:
            score.negative += 2

    address_similarity = similarity(left["address"], right["address"])
    address_state = "missing" if address_similarity is None else (
        "strong_match"
        if address_similarity >= 0.85
        else "similar"
        if address_similarity >= 0.6
        else "conflict"
    )
    evidence.append(
        {
            "field": "address",
            "left": left["address"],
            "right": right["address"],
            "state": address_state,
            "similarity": address_similarity,
        }
    )
    if address_similarity is not None:
        if address_similarity >= 0.85:
            score.positive += 3
        elif address_similarity >= 0.6:
            score.positive += 2
        elif address_similarity >= 0.4:
            score.positive += 1
        elif address_similarity < 0.25:
            score.negative += 2

    phone_state = _value_state(left["telephone"], right["telephone"], normalizer=normalize_phone)
    evidence.append(
        {
            "field": "telephone",
            "left": left["telephone"],
            "right": right["telephone"],
            "state": phone_state,
        }
    )
    if phone_state == "match":
        score.positive += 3
    elif phone_state == "conflict":
        score.negative += 1

    zip_state = _value_state(left["zip_code"], right["zip_code"])
    evidence.append(
        {
            "field": "zip_code",
            "left": left["zip_code"],
            "right": right["zip_code"],
            "state": zip_state,
        }
    )
    if zip_state == "match":
        score.positive += 1
    elif zip_state == "conflict":
        score.negative += 1

    destination_left = left["destination"].get("code")
    destination_right = right["destination"].get("code")
    destination_state = _value_state(destination_left, destination_right)
    evidence.append(
        {
            "field": "destination_code",
            "left": destination_left,
            "right": destination_right,
            "state": destination_state,
        }
    )
    if destination_state == "match":
        score.positive += 1
    elif destination_state == "conflict":
        score.negative += 3

    coordinate_a = left["coordinate"]
    coordinate_b = right["coordinate"]
    distance = None
    coordinate_state = "missing"
    if coordinate_a and coordinate_b:
        distance = round(
            haversine_meters(
                coordinate_a["latitude"],
                coordinate_a["longitude"],
                coordinate_b["latitude"],
                coordinate_b["longitude"],
            ),
            2,
        )
        if distance <= 100:
            coordinate_state = "strong_match"
            score.positive += 3
        elif distance <= 500:
            coordinate_state = "near"
            score.positive += 2
        elif distance <= 1000:
            coordinate_state = "within_1000m"
            score.positive += 1
        elif distance > 5000:
            coordinate_state = "far_apart"
            score.negative += 4
        else:
            coordinate_state = "over_1000m"
            score.negative += 3
    evidence.append(
        {
            "field": "coordinate",
            "left": coordinate_a,
            "right": coordinate_b,
            "state": coordinate_state,
            "distance_meters": distance,
        }
    )

    external_left = left["external_identifiers"]
    external_right = right["external_identifiers"]
    common_keys = sorted(set(external_left) & set(external_right))
    external_matches = [
        key
        for key in common_keys
        if set(external_left[key]) & set(external_right[key])
    ]
    external_conflicts = [
        key
        for key in common_keys
        if not (set(external_left[key]) & set(external_right[key]))
    ]
    if external_matches:
        score.positive += 5
    if external_conflicts:
        score.negative += 3
    evidence.append(
        {
            "field": "external_identifiers",
            "left": external_left,
            "right": external_right,
            "state": (
                "match"
                if external_matches and not external_conflicts
                else "conflict"
                if external_conflicts
                else "missing"
            ),
            "matching_keys": external_matches,
            "conflicting_keys": external_conflicts,
        }
    )

    decision = "manual_review"
    confidence = "low"
    if external_matches and destination_state != "conflict":
        decision = "same_hotel"
        confidence = "high"
        reasons.append("A trusted external mapping identifier matches.")
    elif score.positive >= 8 and score.negative <= 2:
        decision = "same_hotel"
        confidence = "high" if score.positive >= 10 else "medium"
        reasons.append("Multiple independent identity fields strongly agree.")
    elif (
        score.negative >= 6
        and score.positive <= 4
        and (distance is None or distance > 1000)
    ):
        decision = "different_hotels"
        confidence = "high" if score.negative >= 8 else "medium"
        reasons.append("Multiple independent identity fields conflict.")
    elif (
        distance is not None
        and distance > 1000
        and phone_state == "conflict"
        and (address_similarity is None or address_similarity < 0.5)
    ):
        decision = "different_hotels"
        confidence = "medium"
        reasons.append("Coordinates, telephone, and address evidence conflict.")
    else:
        reasons.append("The available evidence is mixed or incomplete.")

    if not left["name"] or not right["name"]:
        decision = "manual_review"
        confidence = "low"
        reasons = ["At least one hotel record lacks a name."]

    return {
        "decision": decision,
        "confidence": confidence,
        "score": {"positive": score.positive, "negative": score.negative},
        "reasons": reasons,
        "evidence": evidence,
        "summaries": [left, right],
    }
