from pathlib import Path
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from dida_hotel_audit.secrets_store import add_access_key
from dida_hotel_audit.server import create_server


class _FakeAuditService:
    def get_hotels(self, hotel_ids, language="en-US"):
        return {
            "ok": True,
            "request": {"hotel_ids": hotel_ids, "language": language},
            "missing_hotel_ids": [],
            "hotels": [
                {"id": hotel_id, "name": f"Synthetic Hotel {hotel_id}"}
                for hotel_id in hotel_ids
            ],
        }

    def get_hotel(self, hotel_id, language="en-US"):
        return {
            "ok": True,
            "request": {"hotel_id": hotel_id, "language": language},
            "hotel": {"id": hotel_id, "name": "Synthetic Hotel"},
        }

    def compare_hotels(self, hotel_id_a, hotel_id_b, language="en-US"):
        return {
            "ok": True,
            "request": {"hotel_ids": [hotel_id_a, hotel_id_b], "language": language},
            "comparison": {"decision": "manual_review"},
            "hotels": [],
        }


@unittest.skipUnless(__import__("os").name == "nt", "Windows DPAPI test")
class GatewayTests(unittest.TestCase):
    def test_gateway_requires_and_accepts_bearer_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "state.dpapi"
            _, key = add_access_key("test", path=store, save_local_client=False)
            server = create_server("127.0.0.1", 0, service=_FakeAuditService(), state_path=store)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                url = f"http://{host}:{port}/v1/compare-hotels"
                payload = json.dumps({"hotel_id_a": 1, "hotel_id_b": 2}).encode("utf-8")
                unauthorized = urllib.request.Request(
                    url, data=payload, method="POST", headers={"Content-Type": "application/json"}
                )
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(unauthorized, timeout=2)
                self.assertEqual(context.exception.code, 401)

                authorized = urllib.request.Request(
                    url,
                    data=payload,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {key}",
                    },
                )
                with urllib.request.urlopen(authorized, timeout=2) as response:
                    result = json.loads(response.read().decode("utf-8"))
                self.assertTrue(result["ok"])
                self.assertEqual(result["request"]["hotel_ids"], [1, 2])

                details_payload = json.dumps({"hotel_id": 3912}).encode("utf-8")
                details = urllib.request.Request(
                    f"http://{host}:{port}/v1/hotel-details",
                    data=details_payload,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {key}",
                    },
                )
                with urllib.request.urlopen(details, timeout=2) as response:
                    details_result = json.loads(response.read().decode("utf-8"))
                self.assertTrue(details_result["ok"])
                self.assertEqual(details_result["hotel"]["id"], 3912)

                batch_payload = json.dumps({"hotel_ids": [3912, 3913]}).encode("utf-8")
                batch = urllib.request.Request(
                    f"http://{host}:{port}/v1/hotels/static",
                    data=batch_payload,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {key}",
                    },
                )
                with urllib.request.urlopen(batch, timeout=2) as response:
                    batch_result = json.loads(response.read().decode("utf-8"))
                self.assertTrue(batch_result["ok"])
                self.assertEqual(
                    [hotel["id"] for hotel in batch_result["hotels"]],
                    [3912, 3913],
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
