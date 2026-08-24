"""Secret storage and access-key management.

On Windows, persisted values are protected with DPAPI and are decryptable only by
the Windows user that created them. Dida credentials are never written as plain
text. Gateway access keys are stored server-side only as SHA-256 digests.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import string
import tempfile
from typing import Any
from urllib.parse import urlsplit


APP_NAME = "dida-hotel-audit"
DEFAULT_GATEWAY_URL = "http://127.0.0.1:8765"
_ENTROPY = b"dida-hotel-audit:dpapi:v1"
_ALPHANUMERIC = string.ascii_letters + string.digits


class SecretStoreError(RuntimeError):
    """Raised when the protected secret store cannot be used."""


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def server_store_path() -> Path:
    override = os.environ.get("DIDA_AUDIT_SERVER_STORE")
    return Path(override) if override else app_data_dir() / "gateway-secrets.dpapi"


def client_store_path() -> Path:
    override = os.environ.get("DIDA_AUDIT_CLIENT_STORE")
    return Path(override) if override else app_data_dir() / "client-access.dpapi"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[_DataBlob, Any]:
    buffer = ctypes.create_string_buffer(data, len(data))
    return (
        _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))),
        buffer,
    )


def _crypt32() -> Any:
    if os.name != "nt":
        raise SecretStoreError(
            "DPAPI storage is available only on Windows. Use runtime environment "
            "variables or a platform secret manager on other systems."
        )
    crypt32 = ctypes.windll.crypt32
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    return crypt32


def protect_bytes(value: bytes) -> bytes:
    crypt32 = _crypt32()
    input_blob, input_buffer = _blob(value)
    entropy_blob, entropy_buffer = _blob(_ENTROPY)
    output_blob = _DataBlob()
    flags = 0x01  # CRYPTPROTECT_UI_FORBIDDEN
    ok = crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        APP_NAME,
        ctypes.byref(entropy_blob),
        None,
        None,
        flags,
        ctypes.byref(output_blob),
    )
    del input_buffer, entropy_buffer
    if not ok:
        raise SecretStoreError(f"DPAPI encryption failed with Windows error {ctypes.GetLastError()}")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)


def unprotect_bytes(value: bytes) -> bytes:
    crypt32 = _crypt32()
    input_blob, input_buffer = _blob(value)
    entropy_blob, entropy_buffer = _blob(_ENTROPY)
    output_blob = _DataBlob()
    description = wintypes.LPWSTR()
    flags = 0x01
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        ctypes.byref(description),
        ctypes.byref(entropy_blob),
        None,
        None,
        flags,
        ctypes.byref(output_blob),
    )
    del input_buffer, entropy_buffer
    if not ok:
        raise SecretStoreError(f"DPAPI decryption failed with Windows error {ctypes.GetLastError()}")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        if description:
            ctypes.windll.kernel32.LocalFree(description)
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _read_protected_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "access_keys": []}
    try:
        decrypted = unprotect_bytes(path.read_bytes())
        state = json.loads(decrypted.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SecretStoreError(f"Protected store is unreadable: {path}") from exc
    if state.get("version") != 1 or not isinstance(state.get("access_keys", []), list):
        raise SecretStoreError(f"Unsupported protected store format: {path}")
    return state


def _write_protected_json(path: Path, value: dict[str, Any]) -> None:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    _atomic_write(path, protect_bytes(encoded))


def load_server_state(path: Path | None = None) -> dict[str, Any]:
    return _read_protected_json(path or server_store_path())


def save_server_state(state: dict[str, Any], path: Path | None = None) -> None:
    _write_protected_json(path or server_store_path(), state)


def set_dida_credentials(client_id: str, license_key: str, path: Path | None = None) -> None:
    client_id = client_id.strip()
    license_key = license_key.strip()
    if not client_id or not license_key:
        raise ValueError("Dida ClientID and LicenseKey must both be non-empty")
    if any(ord(character) < 32 or ord(character) == 127 for character in license_key):
        raise ValueError(
            "Dida LicenseKey contains a control character. The terminal probably "
            "captured a paste shortcut instead of the clipboard text."
        )
    state = load_server_state(path)
    state["dida"] = {"client_id": client_id, "license_key": license_key}
    save_server_state(state, path)


def get_dida_credentials(path: Path | None = None) -> tuple[str, str]:
    env_client = os.environ.get("DIDA_CLIENT_ID")
    env_license = os.environ.get("DIDA_LICENSE_KEY")
    if env_client or env_license:
        if not env_client or not env_license:
            raise SecretStoreError(
                "DIDA_CLIENT_ID and DIDA_LICENSE_KEY must be supplied together"
            )
        return env_client, env_license
    dida = load_server_state(path).get("dida") or {}
    client_id = dida.get("client_id")
    license_key = dida.get("license_key")
    if not client_id or not license_key:
        raise SecretStoreError(
            "Dida credentials are not initialized. Run the hidden credential setup command."
        )
    return str(client_id), str(license_key)


def generate_alphanumeric_key(length: int = 32) -> str:
    if length < 16:
        raise ValueError("Access keys must be at least 16 characters")
    while True:
        value = "".join(secrets.choice(_ALPHANUMERIC) for _ in range(length))
        if any(c.islower() for c in value) and any(c.isupper() for c in value) and any(
            c.isdigit() for c in value
        ):
            return value


def access_key_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def add_access_key(
    label: str,
    *,
    length: int = 32,
    path: Path | None = None,
    save_local_client: bool = True,
    gateway_url: str = DEFAULT_GATEWAY_URL,
) -> tuple[str, str]:
    from datetime import datetime, timezone
    import uuid

    label = label.strip()
    if not label:
        raise ValueError("Access-key label must be non-empty")
    value = generate_alphanumeric_key(length)
    key_id = uuid.uuid4().hex[:12]
    state = load_server_state(path)
    state.setdefault("access_keys", []).append(
        {
            "id": key_id,
            "label": label,
            "sha256": access_key_digest(value),
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_server_state(state, path)
    if save_local_client:
        save_client_access(value, gateway_url=gateway_url)
    return key_id, value


def verify_access_key(value: str, state: dict[str, Any]) -> dict[str, Any] | None:
    candidate = access_key_digest(value)
    for item in state.get("access_keys", []):
        if item.get("enabled") and hmac.compare_digest(str(item.get("sha256", "")), candidate):
            return item
    env_digest = os.environ.get("DIDA_AUDIT_ACCESS_KEY_SHA256")
    if env_digest and hmac.compare_digest(env_digest.lower(), candidate):
        return {"id": "environment", "label": "environment", "enabled": True}
    return None


def revoke_access_key(key_id: str, path: Path | None = None) -> bool:
    state = load_server_state(path)
    changed = False
    for item in state.get("access_keys", []):
        if item.get("id") == key_id and item.get("enabled"):
            item["enabled"] = False
            changed = True
    if changed:
        save_server_state(state, path)
    return changed


def list_access_keys(path: Path | None = None) -> list[dict[str, Any]]:
    safe_items = []
    for item in load_server_state(path).get("access_keys", []):
        safe_items.append(
            {
                "id": item.get("id"),
                "label": item.get("label"),
                "enabled": bool(item.get("enabled")),
                "created_at": item.get("created_at"),
            }
        )
    return safe_items


def save_client_access(
    access_key: str,
    *,
    gateway_url: str = DEFAULT_GATEWAY_URL,
    path: Path | None = None,
) -> None:
    access_key = access_key.strip()
    gateway_url = gateway_url.strip().rstrip("/")
    if not access_key:
        raise ValueError("Audit access key must be non-empty")
    if any(ord(character) < 32 or ord(character) == 127 for character in access_key):
        raise ValueError(
            "Audit access key contains a control character. The terminal probably "
            "captured a paste shortcut instead of the clipboard text."
        )
    parsed = urlsplit(gateway_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Gateway URL must be an HTTP(S) base URL without credentials, query, or fragment")
    value = {"version": 1, "access_key": access_key, "gateway_url": gateway_url}
    _write_protected_json(path or client_store_path(), value)


def load_client_access(path: Path | None = None) -> tuple[str, str]:
    env_key = os.environ.get("DIDA_AUDIT_ACCESS_KEY")
    env_url = os.environ.get("DIDA_AUDIT_GATEWAY_URL", DEFAULT_GATEWAY_URL).rstrip("/")
    if env_key:
        return env_url, env_key
    value = _read_protected_json(path or client_store_path())
    access_key = value.get("access_key")
    if not access_key:
        raise SecretStoreError(
            "Local access key is not configured. Set DIDA_AUDIT_ACCESS_KEY or create a key."
        )
    return str(value.get("gateway_url") or DEFAULT_GATEWAY_URL).rstrip("/"), str(access_key)
