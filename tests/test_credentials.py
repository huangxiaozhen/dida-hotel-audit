import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dida_hotel_audit.cli import main as cli_main
from dida_hotel_audit.credentials import (
    FIXED_DIDA_CLIENT_ID,
    CredentialError,
    credential_status,
    get_dida_credentials,
    save_credentials,
)


class CredentialTests(unittest.TestCase):
    def test_credentials_are_saved_as_plain_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "credentials.json"
            saved = save_credentials(
                "synthetic-license",
                store,
            )
            self.assertEqual(saved, store)
            payload = json.loads(store.read_text(encoding="utf-8"))
            self.assertNotIn("client_id", payload)
            self.assertEqual(payload["license_key"], "synthetic-license")
            self.assertEqual(
                get_dida_credentials(store),
                (FIXED_DIDA_CLIENT_ID, "synthetic-license"),
            )

    def test_status_never_returns_license_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "credentials.json"
            save_credentials("synthetic-license", store)
            result = credential_status(store)
            self.assertTrue(result["configured"])
            self.assertEqual(result["client_id"], FIXED_DIDA_CLIENT_ID)
            self.assertNotIn("license_key", result)
            self.assertNotIn("synthetic-license", json.dumps(result))

    def test_environment_license_key_uses_fixed_client_id(self):
        with patch.dict(
            os.environ,
            {
                "DIDA_CLIENT_ID": "ignored-client",
                "DIDA_LICENSE_KEY": "environment-license",
            },
            clear=False,
        ):
            self.assertEqual(
                get_dida_credentials(Path("not-used.json")),
                (FIXED_DIDA_CLIENT_ID, "environment-license"),
            )
            status = credential_status(Path("not-used.json"))
            self.assertEqual(status["storage"], "environment")
            self.assertIsNone(status["path"])

    def test_missing_license_key_is_rejected(self):
        with patch.dict(
            os.environ,
            {"DIDA_LICENSE_KEY": ""},
            clear=False,
        ):
            with self.assertRaisesRegex(CredentialError, "not configured"):
                get_dida_credentials(Path("not-used.json"))

    def test_cli_set_does_not_echo_license_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "credentials.json"
            output = io.StringIO()
            with patch("sys.stdout", output):
                exit_code = cli_main(
                    [
                        "credentials",
                        "set",
                        "--license-key",
                        "synthetic-license",
                        "--store",
                        str(store),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertNotIn("synthetic-license", output.getvalue())
            self.assertEqual(
                get_dida_credentials(store),
                (FIXED_DIDA_CLIENT_ID, "synthetic-license"),
            )


if __name__ == "__main__":
    unittest.main()
