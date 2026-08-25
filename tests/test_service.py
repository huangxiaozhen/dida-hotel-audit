import unittest

from dida_hotel_audit.service import HotelAuditService


class _FakeDidaClient:
    def __init__(self):
        self.requested_ids = []

    def hotel_details(self, hotel_ids, language="en-US"):
        self.requested_ids.append((hotel_ids, language))
        available = {
            1: {"id": 1, "name": "Hotel One"},
            2: {"id": 2, "name": "Hotel Two"},
        }
        return {
            "traceId": "synthetic-trace",
            "timestamp": "123",
            "data": [available[hotel_id] for hotel_id in reversed(hotel_ids) if hotel_id in available],
        }


class HotelAuditServiceTests(unittest.TestCase):
    def setUp(self):
        self.client = _FakeDidaClient()
        self.service = HotelAuditService(
            credentials_provider=lambda: ("synthetic-client", "synthetic-license"),
            client_factory=lambda _client_id, _license_key: self.client,
        )

    def test_get_hotels_deduplicates_and_preserves_requested_order(self):
        result = self.service.get_hotels([2, 1, 2])
        self.assertTrue(result["ok"])
        self.assertEqual(result["request"]["hotel_ids"], [2, 1])
        self.assertEqual([hotel["id"] for hotel in result["hotels"]], [2, 1])
        self.assertEqual(self.client.requested_ids, [([2, 1], "en-US")])

    def test_get_hotels_reports_missing_ids(self):
        result = self.service.get_hotels([1, 999])
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing_hotel_ids"], [999])
        self.assertEqual([hotel["id"] for hotel in result["hotels"]], [1])

    def test_get_hotels_enforces_batch_limit(self):
        with self.assertRaisesRegex(ValueError, "more than 50"):
            self.service.get_hotels(list(range(1, 52)))

    def test_compare_hotels_passes_suspect_provider_to_comparison(self):
        result = self.service.compare_hotels(
            1,
            2,
            suspect_external_providers=["giata"],
        )
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["request"]["suspect_external_providers"],
            ["giata"],
        )
        self.assertEqual(
            result["comparison"]["suspect_external_providers"],
            ["giata"],
        )


if __name__ == "__main__":
    unittest.main()
