"""Command-line management for the local Dida audit gateway."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import getpass
import json
import logging
import os
from pathlib import Path
import sys

from .secrets_store import (
    DEFAULT_GATEWAY_URL,
    SecretStoreError,
    add_access_key,
    app_data_dir,
    get_dida_credentials,
    load_client_access,
    list_access_keys,
    revoke_access_key,
    save_client_access,
    set_dida_credentials,
)
from .server import create_server


def _path(value: str | None) -> Path | None:
    return Path(value).expanduser().resolve() if value else None


def _open_windows_clipboard() -> tuple[object, object]:
    if os.name != "nt":
        raise OSError("Clipboard credential setup is available only on Windows.")
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    if not user32.OpenClipboard(None):
        raise OSError("Windows clipboard is busy. Close clipboard tools and try again.")
    return user32, kernel32


def _read_windows_clipboard_text() -> str:
    user32, kernel32 = _open_windows_clipboard()
    clipboard_handle = None
    try:
        clipboard_handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
        if not clipboard_handle:
            raise OSError("Windows clipboard does not contain Unicode text.")
        pointer = kernel32.GlobalLock(clipboard_handle)
        if not pointer:
            raise OSError("Windows clipboard text could not be locked.")
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(clipboard_handle)
    finally:
        user32.CloseClipboard()


def _clear_windows_clipboard() -> bool:
    try:
        user32, _ = _open_windows_clipboard()
    except OSError:
        return False
    try:
        return bool(user32.EmptyClipboard())
    finally:
        user32.CloseClipboard()


def _set_credentials(args: argparse.Namespace) -> int:
    clipboard_cleared: bool | None = None
    if args.from_clipboard:
        first = _read_windows_clipboard_text().strip()
        try:
            set_dida_credentials(args.client_id, first, _path(args.store))
        finally:
            first = ""
            clipboard_cleared = _clear_windows_clipboard()
    else:
        first = getpass.getpass("Dida LicenseKey (hidden): ")
        second = getpass.getpass("Confirm Dida LicenseKey (hidden): ")
        if first != second:
            print("Credential confirmation did not match.", file=sys.stderr)
            return 2
        set_dida_credentials(args.client_id, first, _path(args.store))
    print(f"Dida credentials were encrypted for the current Windows user in {app_data_dir()}.")
    if clipboard_cleared:
        print("The Windows clipboard was cleared after encryption.")
    elif clipboard_cleared is False:
        print(
            "Warning: Windows could not clear the clipboard; overwrite it manually.",
            file=sys.stderr,
        )
    return 0


def _credential_status(args: argparse.Namespace) -> int:
    try:
        client_id, _ = get_dida_credentials(_path(args.store))
    except SecretStoreError as exc:
        print(json.dumps({"configured": False, "message": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"configured": True, "client_id": client_id}, ensure_ascii=False))
    return 0


def _configure_client(args: argparse.Namespace) -> int:
    clipboard_cleared: bool | None = None
    if args.from_clipboard:
        first = _read_windows_clipboard_text().strip()
        try:
            save_client_access(
                first,
                gateway_url=args.gateway_url,
                path=_path(args.store),
            )
        finally:
            first = ""
            clipboard_cleared = _clear_windows_clipboard()
    else:
        first = getpass.getpass("Dida Audit access key (hidden): ")
        second = getpass.getpass("Confirm Dida Audit access key (hidden): ")
        if first != second:
            print("Access-key confirmation did not match.", file=sys.stderr)
            return 2
        save_client_access(
            first,
            gateway_url=args.gateway_url,
            path=_path(args.store),
        )
    print(f"Audit client access was encrypted for the current Windows user in {app_data_dir()}.")
    if clipboard_cleared:
        print("The Windows clipboard was cleared after encryption.")
    elif clipboard_cleared is False:
        print(
            "Warning: Windows could not clear the clipboard; overwrite it manually.",
            file=sys.stderr,
        )
    return 0


def _client_status(args: argparse.Namespace) -> int:
    try:
        gateway_url, _ = load_client_access(_path(args.store))
    except SecretStoreError as exc:
        print(json.dumps({"configured": False, "message": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {"configured": True, "gateway_url": gateway_url},
            ensure_ascii=False,
        )
    )
    return 0


def _create_key(args: argparse.Namespace) -> int:
    key_id, value = add_access_key(
        args.label,
        length=args.length,
        path=_path(args.store),
        save_local_client=not args.no_save_client,
        gateway_url=args.gateway_url,
    )
    print(f"Key ID: {key_id}")
    print("Access key (shown once):")
    print(value)
    if not args.no_save_client:
        print("A DPAPI-protected local client copy was saved for this Windows user.")
    return 0


def _list_keys(args: argparse.Namespace) -> int:
    print(json.dumps(list_access_keys(_path(args.store)), ensure_ascii=False, indent=2))
    return 0


def _revoke_key(args: argparse.Namespace) -> int:
    if not revoke_access_key(args.key_id, _path(args.store)):
        print("No enabled access key matched that ID.", file=sys.stderr)
        return 1
    print(f"Revoked access key {args.key_id}.")
    return 0


def _serve(args: argparse.Namespace) -> int:
    if args.host not in ("127.0.0.1", "localhost", "::1") and not args.allow_remote:
        print(
            "Refusing to bind remotely without --allow-remote. Use an authenticated tunnel for team access.",
            file=sys.stderr,
        )
        return 2
    try:
        get_dida_credentials(_path(args.store))
    except SecretStoreError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    server = create_server(args.host, args.port, state_path=_path(args.store))
    print(f"Dida hotel audit gateway listening on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dida-hotel-audit-gateway")
    subparsers = parser.add_subparsers(dest="command", required=True)

    credentials = subparsers.add_parser("credentials", help="Manage encrypted Dida credentials")
    credentials_sub = credentials.add_subparsers(dest="credentials_command", required=True)
    credentials_set = credentials_sub.add_parser(
        "set", help="Set credentials using hidden input or the Windows clipboard"
    )
    credentials_set.add_argument("--client-id", required=True)
    credentials_set.add_argument("--store")
    credentials_set.add_argument(
        "--from-clipboard",
        action="store_true",
        help="read LicenseKey from the Windows clipboard and clear it after encryption",
    )
    credentials_set.set_defaults(handler=_set_credentials)
    credentials_status = credentials_sub.add_parser("status", help="Check credential initialization")
    credentials_status.add_argument("--store")
    credentials_status.set_defaults(handler=_credential_status)

    client = subparsers.add_parser("client", help="Configure this machine as a gateway client")
    client_sub = client.add_subparsers(dest="client_command", required=True)
    client_configure = client_sub.add_parser(
        "configure", help="Store an issued Audit access key with hidden input or the clipboard"
    )
    client_configure.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    client_configure.add_argument("--store")
    client_configure.add_argument(
        "--from-clipboard",
        action="store_true",
        help="read the Audit key from the Windows clipboard and clear it after encryption",
    )
    client_configure.set_defaults(handler=_configure_client)
    client_status = client_sub.add_parser(
        "status", help="Check client initialization without displaying the key"
    )
    client_status.add_argument("--store")
    client_status.set_defaults(handler=_client_status)

    access_key = subparsers.add_parser("access-key", help="Manage gateway access keys")
    access_sub = access_key.add_subparsers(dest="access_command", required=True)
    access_create = access_sub.add_parser("create", help="Create a random access key")
    access_create.add_argument("--label", required=True)
    access_create.add_argument("--length", type=int, default=32)
    access_create.add_argument("--gateway-url", default="http://127.0.0.1:8765")
    access_create.add_argument("--store")
    access_create.add_argument("--no-save-client", action="store_true")
    access_create.set_defaults(handler=_create_key)
    access_list = access_sub.add_parser("list", help="List access-key metadata")
    access_list.add_argument("--store")
    access_list.set_defaults(handler=_list_keys)
    access_revoke = access_sub.add_parser("revoke", help="Revoke an access key")
    access_revoke.add_argument("key_id")
    access_revoke.add_argument("--store")
    access_revoke.set_defaults(handler=_revoke_key)

    serve = subparsers.add_parser("serve", help="Run the local HTTP gateway")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--store")
    serve.add_argument("--allow-remote", action="store_true")
    serve.set_defaults(handler=_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (SecretStoreError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
