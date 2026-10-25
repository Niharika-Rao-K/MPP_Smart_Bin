import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import rates


class RatesApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(rates.router, prefix="/api/rates")
        self.client = TestClient(app)

    def test_latest_rates_uses_newest_timestamp_not_file_order(self):
        history = [
            {
                "material_key": "aluminium can",
                "item": "Aluminium can",
                "fetched_at": "2026-10-24T10:00:00+00:00",
                "status": "OBSERVED",
                "observed_rate_inr_per_kg": 100.0,
            },
            {
                "material_key": "aluminium can",
                "item": "Aluminium can",
                "fetched_at": "2026-10-23T10:00:00+00:00",
                "status": "STALE",
                "observed_rate_inr_per_kg": None,
                "last_known_rate_inr_per_kg": 90.0,
            },
        ]

        with patch.object(rates, "_read_history", return_value=history):
            response = self.client.get("/api/rates")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(
            body["rates"][0]["fetched_at"],
            "2026-10-24T10:00:00+00:00",
        )
        self.assertEqual(
            body["rates"][0]["observed_rate_inr_per_kg"],
            100.0,
        )
        self.assertNotIn("_history_index", body["rates"][0])

    def test_history_endpoint_returns_records_newest_first(self):
        history = [
            {
                "material_key": "can",
                "fetched_at": "2026-10-23T10:00:00+00:00",
            },
            {
                "material_key": "can",
                "fetched_at": "2026-10-24T10:00:00+00:00",
            },
        ]

        with patch.object(rates, "_read_history", return_value=history):
            response = self.client.get("/api/rates/history")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        self.assertGreater(
            body["history"][0]["fetched_at"],
            body["history"][1]["fetched_at"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
