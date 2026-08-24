"""Minimal Dida Content API v2 client with redacted errors."""

from __future__ import annotations

import base64
import gzip
import json
import ssl
from typing import Any
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "https://static-api.didatravel.com"


class DidaAPIError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


class DidaClient:
    def __init__(
        self,
        client_id: str,
        license_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        if not client_id or not license_key:
            raise ValueError("Dida credentials must be non-empty")
        self._client_id = client_id
        self._license_key = license_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def hotel_details(self, hotel_ids: list[int], language: str = "en-US") -> dict[str, Any]:
        if not hotel_ids or len(hotel_ids) > 50:
            raise ValueError("hotel_ids must contain between 1 and 50 IDs")
        if any(not isinstance(item, int) or item <= 0 for item in hotel_ids):
            raise ValueError("Every hotel ID must be a positive integer")
        payload = json.dumps(
            {"language": language, "hotelIds": hotel_ids}, separators=(",", ":")
        ).encode("utf-8")
        credential = base64.b64encode(
            f"{self._client_id}:{self._license_key}".encode("utf-8")
        ).decode("ascii")
        request = urllib.request.Request(
            f"{self._base_url}/api/v1/hotel/details",
            data=payload,
            method="POST",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "Authorization": f"Basic {credential}",
                "Content-Type": "application/json",
                "User-Agent": "dida-hotel-audit/0.1",
            },
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout, context=ssl.create_default_context()
            ) as response:
                body = response.read()
                if response.headers.get("Content-Encoding", "").lower() == "gzip":
                    body = gzip.decompress(body)
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise DidaAPIError(
                f"Dida Content API returned HTTP {exc.code}", status=exc.code
            ) from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            reason_name = type(reason).__name__ if reason is not None else "network error"
            raise DidaAPIError(f"Dida Content API request failed: {reason_name}") from exc
        except (gzip.BadGzipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DidaAPIError("Dida Content API returned an invalid JSON response") from exc
