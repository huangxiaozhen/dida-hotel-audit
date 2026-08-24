import json
from pathlib import Path
import re
import tempfile
import unittest

from dida_hotel_audit.secrets_store import (
    access_key_digest,
    add_access_key,
    get_dida_credentials,
    load_client_access,
    load_server_state,
    protect_bytes,
    save_client_access,
    set_dida_credentials,
    unprotect_bytes,
    verify_access_key,
)


@unittest.skipUnless(__import__("os").name == "nt", "Windows DPAPI test")
class SecretStoreTests(unittest.TestCase):
    def test_dpapi_round_trip_does_not_store_plaintext(self):
        plaintext = b"synthetic-secret-value"
        encrypted = protect_bytes(plaintext)
        self.assertNotIn(plaintext, encrypted)
        self.assertEqual(unprotect_bytes(encrypted), plaintext)

    def test_credentials_and_access_key_are_protected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "state.dpapi"
            set_dida_credentials("synthetic-client", "synthetic-license", store)
            key_id, access_key = add_access_key(
                "test-owner", path=store, save_local_client=False
            )
            raw = store.read_bytes()
            self.assertNotIn(b"synthetic-license", raw)
            self.assertNotIn(access_key.encode("ascii"), raw)
            self.assertRegex(access_key, re.compile(r"^[A-Za-z0-9]{32}$"))
            self.assertEqual(get_dida_credentials(store), ("synthetic-client", "synthetic-license"))
            state = load_server_state(store)
            self.assertEqual(verify_access_key(access_key, state)["id"], key_id)
            self.assertNotIn(access_key, json.dumps(state))
            self.assertIn(access_key_digest(access_key), json.dumps(state))

    def test_credentials_reject_paste_control_character(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "state.dpapi"
            with self.assertRaisesRegex(ValueError, "control character"):
                set_dida_credentials("synthetic-client", "\x16", store)
            self.assertFalse(store.exists())

    def test_client_access_is_protected_and_loadable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "client.dpapi"
            save_client_access(
                "synthetic-audit-key",
                gateway_url="https://audit.example.test/",
                path=store,
            )
            raw = store.read_bytes()
            self.assertNotIn(b"synthetic-audit-key", raw)
            self.assertEqual(
                load_client_access(store),
                ("https://audit.example.test", "synthetic-audit-key"),
            )

    def test_client_access_rejects_unsafe_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "client.dpapi"
            with self.assertRaisesRegex(ValueError, "without credentials"):
                save_client_access(
                    "synthetic-audit-key",
                    gateway_url="https://user:password@example.test",
                    path=store,
                )
            self.assertFalse(store.exists())


if __name__ == "__main__":
    unittest.main()
