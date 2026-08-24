"""Local HTTP gateway for authenticated hotel comparison requests."""

from __future__ import annotations

from collections import defaultdict, deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any
from urllib.parse import urlsplit

from .dida_client import DidaAPIError
from .secrets_store import (
    SecretStoreError,
    get_dida_credentials,
    load_server_state,
    verify_access_key,
)
from .service import HotelAuditService


LOGGER = logging.getLogger("dida_hotel_audit.gateway")
MAX_REQUEST_BYTES = 64 * 1024


class SlidingWindowRateLimiter:
    def __init__(self, requests: int = 30, window_seconds: float = 60.0) -> None:
        self._requests = requests
        self._window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key_id: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            events = self._events[key_id]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self._requests:
                return False
            events.append(now)
            return True


class GatewayHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        service: HotelAuditService | None = None,
        state_path: Path | None = None,
        rate_limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        super().__init__(server_address, GatewayRequestHandler)
        self.audit_service = service or HotelAuditService()
        self.state_path = state_path
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter()


class GatewayRequestHandler(BaseHTTPRequestHandler):
    server: GatewayHTTPServer
    protocol_version = "HTTP/1.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _discard_request_body(self) -> None:
        """Drain a bounded unauthenticated body so Windows does not reset the socket."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if 0 < length <= MAX_REQUEST_BYTES:
            self.rfile.read(length)

    def _authenticate(self) -> dict[str, Any] | None:
        header = self.headers.get("Authorization", "")
        scheme, separator, value = header.partition(" ")
        if not separator or scheme.casefold() != "bearer" or not value.strip():
            self._discard_request_body()
            self._send_json(
                HTTPStatus.UNAUTHORIZED,
                {"ok": False, "error": {"code": "unauthorized", "message": "Bearer key required"}},
            )
            return None
        try:
            state = load_server_state(self.server.state_path)
        except SecretStoreError:
            self._discard_request_body()
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "ok": False,
                    "error": {"code": "gateway_not_initialized", "message": "Gateway secrets are unavailable"},
                },
            )
            return None
        identity = verify_access_key(value.strip(), state)
        if identity is None:
            self._discard_request_body()
            self._send_json(
                HTTPStatus.UNAUTHORIZED,
                {"ok": False, "error": {"code": "unauthorized", "message": "Invalid access key"}},
            )
            return None
        if not self.server.rate_limiter.allow(str(identity.get("id"))):
            self._discard_request_body()
            self._send_json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"ok": False, "error": {"code": "rate_limited", "message": "Too many requests"}},
            )
            return None
        return identity

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {"ok": True, "service": "dida-hotel-audit", "version": "0.1.0"},
            )
            return
        self._send_json(
            HTTPStatus.NOT_FOUND,
            {"ok": False, "error": {"code": "not_found", "message": "Endpoint not found"}},
        )

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path not in (
            "/v1/compare-hotels",
            "/v1/hotel-details",
            "/v1/hotels/static",
        ):
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"ok": False, "error": {"code": "not_found", "message": "Endpoint not found"}},
            )
            return
        if self._authenticate() is None:
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": {"code": "invalid_request", "message": "Invalid request size"}},
            )
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            language = payload.get("language", "en-US")
            if path == "/v1/hotels/static":
                raw_hotel_ids = payload.get("hotel_ids")
                if not isinstance(raw_hotel_ids, list):
                    raise ValueError("hotel_ids must be a JSON array")
                result = self.server.audit_service.get_hotels(
                    raw_hotel_ids, language=language
                )
            elif path == "/v1/hotel-details":
                hotel_id = int(payload.get("hotel_id"))
                result = self.server.audit_service.get_hotel(hotel_id, language=language)
            else:
                hotel_id_a = int(payload.get("hotel_id_a"))
                hotel_id_b = int(payload.get("hotel_id_b"))
                result = self.server.audit_service.compare_hotels(
                    hotel_id_a, hotel_id_b, language=language
                )
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": {"code": "invalid_request", "message": str(exc)}},
            )
            return
        except SecretStoreError:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "ok": False,
                    "error": {
                        "code": "dida_credentials_unavailable",
                        "message": "Dida credentials are not initialized",
                    },
                },
            )
            return
        except DidaAPIError as exc:
            status = HTTPStatus.BAD_GATEWAY
            if exc.status in (401, 403):
                status = HTTPStatus.SERVICE_UNAVAILABLE
            self._send_json(
                status,
                {
                    "ok": False,
                    "error": {"code": "dida_api_error", "message": str(exc)},
                },
            )
            return
        except Exception:
            LOGGER.exception("Unhandled gateway error (credentials and request bodies are not logged)")
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": {"code": "internal_error", "message": "Internal gateway error"}},
            )
            return
        self._send_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: Any) -> None:
        safe_path = urlsplit(self.path).path
        LOGGER.info("client=%s method=%s path=%s", self.client_address[0], self.command, safe_path)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    service: HotelAuditService | None = None,
    state_path: Path | None = None,
) -> GatewayHTTPServer:
    if service is None and state_path is not None:
        service = HotelAuditService(
            credentials_provider=lambda: get_dida_credentials(state_path)
        )
    return GatewayHTTPServer((host, port), service=service, state_path=state_path)
