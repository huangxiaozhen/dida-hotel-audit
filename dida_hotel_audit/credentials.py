"""Plain-text local credential storage for direct Dida API access."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


APP_NAME = "dida-hotel-audit"
FIXED_DIDA_CLIENT_ID = "Huangzhen_test"


class CredentialError(RuntimeError):
    """Raised when Dida credentials are missing or invalid."""


def config_dir() -> Path:
    """Return the per-user configuration directory used by this Skill."""
    override = os.environ.get("DIDA_HOTEL_AUDIT_CONFIG_DIR")
    if override:
        return Path(override).expanduser()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local_app_data:
        return Path(local_app_data) / APP_NAME

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser() / APP_NAME

    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".config" / APP_NAME


def sys_platform() -> str:
    """Small wrapper kept separate so platform path behavior is easy to test."""
    import sys

    return sys.platform


def credentials_path() -> Path:
    override = os.environ.get("DIDA_HOTEL_AUDIT_CREDENTIALS_FILE")
    return Path(override).expanduser() if override else config_dir() / "credentials.json"


def _validated_value(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} must be non-empty")
    if any(ord(character) < 32 or ord(character) == 127 for character in cleaned):
        raise ValueError(f"{label} contains a control character")
    return cleaned


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        # This is not encryption. It only limits ordinary file access on systems
        # that honor POSIX permission bits.
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def save_credentials(
    license_key: str,
    path: Path | None = None,
) -> Path:
    """Save the Dida LicenseKey as plain JSON outside the Skill repository."""
    destination = path or credentials_path()
    payload = {
        "version": 1,
        "license_key": _validated_value(license_key, "Dida LicenseKey"),
    }
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_write(destination, encoded)
    return destination


def _load_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CredentialError(
            "Dida credentials are not configured. Run scripts/configure.py first."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CredentialError(f"Dida credential file is unreadable: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise CredentialError(f"Unsupported Dida credential file format: {path}")
    return payload


def get_dida_credentials(path: Path | None = None) -> tuple[str, str]:
    """Return the fixed ClientID and a configured LicenseKey."""
    env_license = os.environ.get("DIDA_LICENSE_KEY")
    if env_license:
        try:
            return (
                FIXED_DIDA_CLIENT_ID,
                _validated_value(env_license, "Dida LicenseKey"),
            )
        except ValueError as exc:
            raise CredentialError("Runtime Dida LicenseKey is invalid") from exc

    source = path or credentials_path()
    payload = _load_file(source)
    try:
        return (
            FIXED_DIDA_CLIENT_ID,
            _validated_value(str(payload.get("license_key") or ""), "Dida LicenseKey"),
        )
    except ValueError as exc:
        raise CredentialError(f"Dida LicenseKey file is incomplete: {source}") from exc


def credential_status(path: Path | None = None) -> dict[str, Any]:
    if os.environ.get("DIDA_LICENSE_KEY"):
        client_id, _ = get_dida_credentials(path)
        return {
            "configured": True,
            "client_id": client_id,
            "storage": "environment",
            "path": None,
        }
    source = path or credentials_path()
    client_id, _ = get_dida_credentials(path)
    return {
        "configured": True,
        "client_id": client_id,
        "storage": "plaintext_json",
        "path": str(source.resolve()),
    }
