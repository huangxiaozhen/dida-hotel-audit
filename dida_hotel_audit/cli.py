"""Command-line setup for direct Dida hotel static-content access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .credentials import (
    FIXED_DIDA_CLIENT_ID,
    CredentialError,
    credential_status,
    save_credentials,
)


def _path(value: str | None) -> Path | None:
    return Path(value).expanduser().resolve() if value else None


def _set_credentials(args: argparse.Namespace) -> int:
    destination = save_credentials(
        args.license_key,
        _path(args.store),
    )
    print(
        json.dumps(
            {
                "configured": True,
                "client_id": FIXED_DIDA_CLIENT_ID,
                "storage": "plaintext_json",
                "path": str(destination.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _credential_status(args: argparse.Namespace) -> int:
    try:
        result = credential_status(_path(args.store))
    except CredentialError as exc:
        print(
            json.dumps(
                {"configured": False, "message": str(exc)},
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dida-hotel-audit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    credentials = subparsers.add_parser(
        "credentials", help="Manage the local plain-text Dida credentials"
    )
    credentials_sub = credentials.add_subparsers(
        dest="credentials_command", required=True
    )

    credentials_set = credentials_sub.add_parser(
        "set", help="Save the LicenseKey as plain JSON outside the repository"
    )
    credentials_set.add_argument("--license-key", required=True)
    credentials_set.add_argument("--store")
    credentials_set.set_defaults(handler=_set_credentials)

    credentials_status_parser = credentials_sub.add_parser(
        "status", help="Check setup without displaying the LicenseKey"
    )
    credentials_status_parser.add_argument("--store")
    credentials_status_parser.set_defaults(handler=_credential_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (CredentialError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
