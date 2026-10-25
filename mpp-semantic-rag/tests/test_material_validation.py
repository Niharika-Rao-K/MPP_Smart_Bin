import json
import unittest
from pathlib import Path

from app.services.material_validation import validate_material_candidate


KNOWLEDGE_PATH = Path(__file__).resolve().parents[1] / "data" / "waste_knowledge.json"


class MaterialValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profiles = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
        cls.profiles = {profile["item"]: profile for profile in profiles}

    def validate(self, item, weight):
        return validate_material_candidate(self.profiles[item], weight)

    def test_reference_rate_and_compatible_weight(self):
        result = self.validate("Coca-Cola 330ml aluminum can", 14.0)

        self.assertEqual(result["status"], "WEIGHT_COMPATIBLE")
        self.assertTrue(result["weight_compatible"])
        self.assertTrue(result["automatic_rate_eligible"])

    def test_weight_below_expected_range(self):
        result = self.validate("Coca-Cola 330ml aluminum can", 11.0)

        self.assertEqual(result["status"], "WEIGHT_MISMATCH")
        self.assertFalse(result["weight_compatible"])

    def test_weight_above_expected_range(self):
        result = self.validate("Coca-Cola 330ml aluminum can", 22.5)

        self.assertEqual(result["status"], "WEIGHT_MISMATCH")
        self.assertFalse(result["weight_compatible"])

    def test_exact_weight_range_boundaries_are_inclusive(self):
        lower = self.validate("Coca-Cola 330ml aluminum can", 11.2)
        upper = self.validate("Coca-Cola 330ml aluminum can", 16.8)

        self.assertTrue(lower["weight_compatible"])
        self.assertTrue(upper["weight_compatible"])

    def test_fallback_rate_requires_review(self):
        result = self.validate("Snack wrapper", 5.0)

        self.assertEqual(result["status"], "RATE_REVIEW_REQUIRED")
        self.assertTrue(result["weight_compatible"])
        self.assertFalse(result["automatic_rate_eligible"])


    def test_reference_rate_allows_automatic_eligibility(self):
        result = self.validate("Samsung RAM stick", 18.0)

        self.assertEqual(result["status"], "WEIGHT_COMPATIBLE")
        self.assertTrue(result["weight_compatible"])
        self.assertTrue(result["automatic_rate_eligible"])


    def test_unknown_rate_status_requires_review(self):
        profile = dict(self.profiles["Coca-Cola 330ml aluminum can"])
        profile["rate_status"] = "unverified"

        result = validate_material_candidate(profile, 14.0)

        self.assertEqual(result["status"], "RATE_REVIEW_REQUIRED")
        self.assertFalse(result["automatic_rate_eligible"])

    def test_zero_weight_is_rejected(self):
        result = self.validate("Coca-Cola 330ml aluminum can", 0.0)

        self.assertEqual(result["status"], "REJECTED")
        self.assertFalse(result["weight_compatible"])
        self.assertFalse(result["automatic_rate_eligible"])

    def test_negative_weight_is_rejected(self):
        result = self.validate("Coca-Cola 330ml aluminum can", -1.0)

        self.assertEqual(result["status"], "REJECTED")

    def test_weight_check_does_not_claim_purity_or_brand(self):
        result = self.validate("Coca-Cola 330ml aluminum can", 14.0)

        self.assertFalse(result["purity_verified"])
        self.assertFalse(result["brand_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
