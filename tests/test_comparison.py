import unittest

from dida_hotel_audit.comparison import (
    compare_hotel_records,
    haversine_meters,
    hotel_name_similarity,
)


class ComparisonTests(unittest.TestCase):
    def test_same_hotel_from_multiple_independent_fields(self):
        left = {
            "id": 101,
            "name": "Example Grand Hotel",
            "location": {
                "address": "5 Central Avenue",
                "destination": {"code": "9001", "name": "Example City"},
                "coordinate": {"latitude": 40.0, "longitude": 65.0},
            },
            "telephone": "+1 555 0100",
            "zipCode": "10001",
            "giataCode": "778899",
        }
        right = {
            "id": 202,
            "name": "EXAMPLE GRAND HOTEL",
            "location": {
                "address": "5 Central Ave.",
                "destination": {"code": "9001", "name": "Example City"},
                "coordinate": {"latitude": 40.0001, "longitude": 65.0001},
            },
            "telephone": "001-555-0100",
            "zipCode": "10001",
            "giataCode": "778899",
        }
        result = compare_hotel_records(left, right)
        self.assertEqual(result["decision"], "same_hotel")
        self.assertEqual(result["confidence"], "high")

    def test_different_hotels_from_combined_conflicts(self):
        left = {
            "id": 101,
            "name": "Central Plaza Hotel",
            "location": {
                "address": "1 North Street",
                "destination": {"code": "9001"},
                "coordinate": {"latitude": 40.0000, "longitude": 65.0000},
            },
            "telephone": "+1 555 0100",
            "zipCode": "10001",
            "vervotechCodes": ["111"],
        }
        right = {
            "id": 202,
            "name": "Central Plaza Resort",
            "location": {
                "address": "88 Industrial Village",
                "destination": {"code": "9001"},
                "coordinate": {"latitude": 40.02, "longitude": 65.02},
            },
            "telephone": "+1 555 9999",
            "zipCode": "10999",
            "vervotechCodes": ["222"],
        }
        result = compare_hotel_records(left, right)
        self.assertEqual(result["decision"], "different_hotels")
        coordinate = next(item for item in result["evidence"] if item["field"] == "coordinate")
        self.assertGreater(coordinate["distance_meters"], 1000)
        external = next(
            item for item in result["evidence"] if item["field"] == "external_identifiers"
        )
        self.assertEqual(external["state"], "conflict")
        self.assertEqual(external["left"]["vervotech"], ["111"])
        self.assertEqual(external["right"]["vervotech"], ["222"])

    def test_name_similarity_tolerates_location_suffix_and_word_order(self):
        score = hotel_name_similarity(
            "ZARAFSHAN GRAND HOTEL", "Grand Hotel Zarafshan In Fiez Navoi"
        )
        self.assertEqual(score, 1.0)

    def test_name_alone_stays_manual_review(self):
        left = {"id": 101, "name": "Example Hotel"}
        right = {"id": 202, "name": "Example Hotel"}
        result = compare_hotel_records(left, right)
        self.assertEqual(result["decision"], "manual_review")

    def test_suspect_giata_mapping_is_excluded_from_identity_scoring(self):
        left = {
            "id": 101,
            "name": "Example Grand Hotel",
            "location": {
                "address": "1 North Street",
                "destination": {"code": "9001"},
                "coordinate": {"latitude": 40.0, "longitude": 65.0},
            },
            "telephone": "+1 555 0100",
            "zipCode": "10001",
            "giataCode": "778899",
        }
        right = {
            "id": 202,
            "name": "Example Grand Hotel",
            "location": {
                "address": "88 Industrial Village",
                "destination": {"code": "9001"},
                "coordinate": {"latitude": 41.0, "longitude": 66.0},
            },
            "telephone": "+1 555 9999",
            "zipCode": "10999",
            "giataCode": "778899",
        }

        trusted_result = compare_hotel_records(left, right)
        audited_result = compare_hotel_records(
            left,
            right,
            suspect_external_providers=["GIATA Code"],
        )

        self.assertEqual(trusted_result["decision"], "same_hotel")
        self.assertEqual(audited_result["decision"], "different_hotels")
        external = next(
            item
            for item in audited_result["evidence"]
            if item["field"] == "external_identifiers"
        )
        self.assertEqual(external["state"], "excluded_from_decision")
        self.assertEqual(external["suspect_matching_keys"], ["giata"])
        self.assertEqual(external["matching_keys"], [])

    def test_haversine_known_short_distance(self):
        distance = haversine_meters(40.0, 65.0, 40.0001, 65.0001)
        self.assertGreater(distance, 10)
        self.assertLess(distance, 20)


if __name__ == "__main__":
    unittest.main()
