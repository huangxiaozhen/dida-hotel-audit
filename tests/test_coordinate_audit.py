import unittest

from dida_hotel_audit.coordinate_audit import audit_hotel_coordinate


class CoordinateAuditTests(unittest.TestCase):
    def test_coordinate_audit_uses_haversine_and_threshold(self):
        hotel = {
            "id": 3912,
            "name": "Synthetic Hotel",
            "location": {
                "address": "1 Example Road",
                "coordinate": {"latitude": 40.0, "longitude": 65.0},
            },
        }
        result = audit_hotel_coordinate(hotel, 40.0001, 65.0001)
        self.assertGreater(result["distance_meters"], 10)
        self.assertLess(result["distance_meters"], 20)
        self.assertTrue(result["within_threshold"])
        self.assertEqual(result["threshold_meters"], 1000)

    def test_coordinate_audit_rejects_invalid_reference(self):
        hotel = {
            "id": 3912,
            "location": {"coordinate": {"latitude": 40.0, "longitude": 65.0}},
        }
        with self.assertRaisesRegex(ValueError, "latitude"):
            audit_hotel_coordinate(hotel, 91, 65)


if __name__ == "__main__":
    unittest.main()
