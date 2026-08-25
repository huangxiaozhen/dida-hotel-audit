#!/usr/bin/env python3
"""Save the Dida LicenseKey as a local plain-text configuration."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dida_hotel_audit.cli import main as cli_main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(cli_main(["credentials", "set", *sys.argv[1:]]))
