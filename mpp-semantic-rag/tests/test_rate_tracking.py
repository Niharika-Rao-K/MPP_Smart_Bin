import json
import tempfile
import unittest
from pathlib import Path

from app.services.rate_tracking import (
    extract_rate_inr_per_kg,
    refresh_rate_snapshots,
)


class RateTrackingTests(unittest.TestCase):
    def test_extracts_explicit_rupee_rate(self):
        self.assertEqual(
            extract_rate_inr_per_kg("Aluminium scrap: \u20b9136 per kg"),
            136.0,
        )

    def test_extracts_inr_rate(self):
        self.assertEqual(
            extract_rate_inr_per_kg("Current rate INR 1,250/kg"),
            1250.0,
        )

    def test_rejects_bare_number(self):
        self.assertIsNone(extract_rate_inr_per_kg("Rate today is 136"))

    def test_rejects_ambiguous_multiple_rates(self):
        text = "Aluminium \u20b9136/kg; copper \u20b9700/kg"
        self.assertIsNone(extract_rate_inr_per_kg(text))

    def test_rejects_zero_rate(self):
        self.assertIsNone(extract_rate_inr_per_kg("\u20b90/kg"))

    def test_fetches_shared_source_only_once(self):
        calls = []
        profiles = [
            {
                "item": "Can A",
                "rate_inr_per_kg": 100,
                "rate_source_url": "https://example.test/aluminium",
            },
            {
                "item": "Can B",
                "rate_inr_per_kg": 100,
                "rate_source_url": "https://example.test/aluminium",
            },
        ]

        def fake_fetch(url):
            calls.append(url)
            return {
                "status": "fetched",
                "text_excerpt": "Aluminium rate \u20b9136/kg",
            }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            result = refresh_rate_snapshots(
                profiles, path, fake_fetch, now="2026-10-24T10:00:00+00:00"
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["status"], "OBSERVED")
            self.assertEqual(result[0]["observed_rate_inr_per_kg"], 136.0)
            self.assertEqual(result[1]["observed_rate_inr_per_kg"], 136.0)

    def test_cached_rate_is_marked_cached(self):
        profile = {
            "item": "Aluminium can",
            "rate_inr_per_kg": 100,
            "rate_source_url": "https://example.test/aluminium",
        }

        with tempfile.TemporaryDirectory() as directory:
            result = refresh_rate_snapshots(
                [profile],
                Path(directory) / "history.json",
                lambda url: {
                    "status": "cached",
                    "text_excerpt": "Aluminium rate INR 136/kg",
                },
                now="2026-10-24T10:00:00+00:00",
            )

        self.assertEqual(result[0]["status"], "CACHED")
        self.assertEqual(
            result[0]["observed_rate_inr_per_kg"], 136.0
        )
        self.assertEqual(
            result[0]["last_known_rate_inr_per_kg"], 136.0
        )
    def test_failed_refresh_preserves_last_observed_rate_as_stale(self):
        profile = {
            "item": "Aluminium can",
            "rate_inr_per_kg": 100,
            "rate_source_url": "https://example.test/aluminium",
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"

            refresh_rate_snapshots(
                [profile],
                path,
                lambda url: {
                    "status": "fetched",
                    "text_excerpt": "Aluminium \u20b9136/kg",
                },
                now="2026-10-24T10:00:00+00:00",
            )

            result = refresh_rate_snapshots(
                [profile],
                path,
                lambda url: {
                    "status": "unavailable",
                    "text_excerpt": "",
                },
                now="2026-10-25T10:00:00+00:00",
            )

            self.assertEqual(result[0]["status"], "STALE")
            self.assertIsNone(result[0]["observed_rate_inr_per_kg"])
            self.assertEqual(
                result[0]["last_known_rate_inr_per_kg"], 136.0
            )

            history = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(history), 2)

    def test_first_failure_keeps_baseline_unverified(self):
        profile = {
            "item": "Snack wrapper",
            "rate_inr_per_kg": 14.56,
            "rate_source_url": "https://example.test/plastic",
        }

        with tempfile.TemporaryDirectory() as directory:
            result = refresh_rate_snapshots(
                [profile],
                Path(directory) / "history.json",
                lambda url: {
                    "status": "unavailable",
                    "text_excerpt": "",
                },
            )

        self.assertEqual(result[0]["status"], "BASELINE_UNVERIFIED")
        self.assertEqual(
            result[0]["last_known_rate_inr_per_kg"], 14.56
        )
        self.assertIsNone(result[0]["observed_rate_inr_per_kg"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
