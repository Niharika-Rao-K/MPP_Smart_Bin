import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.database.models import (
    Bin,
    Deposit,
    SensorReading,
    SegregationCommand,
    MechanicalReferenceAssessment,
)
from app.routes import deposit as deposit_route
from app.services import mechanical_fingerprint_service as mechanical_service
from app.services.mechanical_fingerprint_service import (
    assess_mechanical_fingerprint,
)


class MechanicalFingerprintServiceTests(unittest.TestCase):

    def test_diet_coke_can_uses_its_exact_reference(self):
        reference_median_features = {
            "peak_g": 24.5624,
            "early_rms_g": 15.4459,
            "area_g_seconds": 110.7268,
            "stable_weight_g": 14.0833,
        }

        with patch.object(
            mechanical_service,
            "_extract_features",
            return_value=reference_median_features,
        ):
            result = assess_mechanical_fingerprint(
                image_label="diet_coke",
                stable_weight_g=14.0833,
                baseline_mean_g=0.0,
                raw_samples=[{"t_ms": i * 100, "weight_g": 0.0} for i in range(10)],
                impact_sample_count=10,
            )

        self.assertEqual(result["status"], "SHADOW_ASSESSED")
        self.assertEqual(result["assessment_mode"], "SHADOW_ONLY")
        self.assertEqual(result["image_label"], "diet_coke")
        self.assertEqual(result["image_expected_class"], "Metal")
        self.assertTrue(result["mechanical_agreement"])
        self.assertEqual(result["matched_feature_count"], 4)
        self.assertEqual(result["total_feature_count"], 4)
        self.assertEqual(
            set(result["extracted_features"]),
            {"peak_g", "early_rms_g", "area_g_seconds", "stable_weight_g"},
        )

    def test_ram_stick_uses_its_exact_reference(self):
        reference_median_features = {
            "peak_g": 17.2007,
            "early_rms_g": 14.9391,
            "area_g_seconds": 112.6561,
            "stable_weight_g": 15.3663,
        }

        with patch.object(
            mechanical_service,
            "_extract_features",
            return_value=reference_median_features,
        ):
            result = assess_mechanical_fingerprint(
                image_label="ram_stick",
                stable_weight_g=15.3663,
                baseline_mean_g=0.0,
                raw_samples=[{"t_ms": i * 100, "weight_g": 0.0} for i in range(10)],
                impact_sample_count=10,
            )

        self.assertEqual(result["status"], "SHADOW_ASSESSED")
        self.assertEqual(result["assessment_mode"], "SHADOW_ONLY")
        self.assertEqual(result["image_label"], "ram_stick")
        self.assertEqual(result["image_expected_class"], "E-Waste")
        self.assertTrue(result["mechanical_agreement"])
        self.assertEqual(result["matched_feature_count"], 4)
        self.assertEqual(result["total_feature_count"], 4)

    def test_unsupported_label_is_not_applicable(self):
        for label in (
            "pepsi_can",
            "coca_cola_can",
            "general_metal",
            "snickers_wrapper",
        ):
            with self.subTest(label=label):
                result = assess_mechanical_fingerprint(
                    image_label=label,
                    stable_weight_g=14.0,
                    impact_sample_count=72,
                )
                self.assertEqual(result["status"], "NOT_APPLICABLE")

    def test_missing_raw_samples_is_insufficient_data(self):
        result = assess_mechanical_fingerprint(
            image_label="ram_stick",
            stable_weight_g=12.5,
            baseline_mean_g=0.0,
            raw_samples=None,
            impact_sample_count=72,
        )

        self.assertEqual(result["status"], "INSUFFICIENT_DATA")

    def test_non_finite_stable_weight_is_insufficient_data(self):
        result = assess_mechanical_fingerprint(
            image_label="diet_coke",
            stable_weight_g=float("nan"),
            baseline_mean_g=0.0,
            raw_samples=[{"t_ms": i * 100, "weight_g": 0.0} for i in range(10)],
            impact_sample_count=10,
        )

        self.assertEqual(result["status"], "INSUFFICIENT_DATA")

    def test_invalid_sample_count_is_insufficient_data(self):
        result = assess_mechanical_fingerprint(
            image_label="diet_coke",
            stable_weight_g=14.0,
            baseline_mean_g=0.0,
            raw_samples=[],
            impact_sample_count=0,
        )

        self.assertEqual(result["status"], "INSUFFICIENT_DATA")


class MechanicalFingerprintDepositShadowTests(unittest.TestCase):

    WALLET = "0x" + ("1" * 40)

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        Base.metadata.create_all(bind=self.engine)

        self.TestSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

        self.app = FastAPI()
        self.app.include_router(
            deposit_route.router,
            prefix="/api/rag",
        )

        def override_get_db():
            db = self.TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[
            deposit_route.get_db
        ] = override_get_db

        self.client = TestClient(self.app)

        self.original_session_local = deposit_route.SessionLocal
        deposit_route.SessionLocal = self.TestSessionLocal

        db = self.TestSessionLocal()
        try:
            bin_record = Bin(
                bin_code="BIN001",
                location="Test Location",
                status="ACTIVE",
            )
            db.add(bin_record)

            reading = SensorReading(
                bin_code="BIN001",
                sensor_id="test-sensor",
                reading_id="TEST-READING-001",
                weight_g=14.4458,
                impact_peak_g=38.2773,
                impact_settling_ms=877,
                impact_sample_count=72,
                impact_variation_index=0.5,
                consumed=False,
                created_at=datetime.now(timezone.utc),
            )
            db.add(reading)
            db.commit()
        finally:
            db.close()

    def tearDown(self):
        deposit_route.SessionLocal = self.original_session_local
        self.client.close()
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    @staticmethod
    def accepted_fusion_result():
        return {
            "visual_label": "diet_coke",
            "actual_weight_g": 14.4458,
            "rag_result": {
                "final_decision": {
                    "status": "ACCEPTED",
                    "reward_eligible": True,
                    "hardware_route_signal": "M",
                },
            },
            "decision": "ACCEPTED",
            "action": "Accept item.",
            "hardware_route_signal": "M",
            "reward_eligible": True,
        }

    @staticmethod
    def assessment_disagrees_with_image():
        return {
            "model_name": "item_specific_mechanical_reference",
            "model_version": "four_feature_reference_v1",
            "status": "SHADOW_ASSESSED",
            "assessment_mode": "SHADOW_ONLY",
            "image_label": "diet_coke",
            "image_expected_class": "Metal",
            "mechanical_agreement": False,
            "extracted_features": {
                "peak_g": 20.0,
                "early_rms_g": 16.0,
                "area_g_seconds": 100.0,
                "stable_weight_g": 14.4458,
            },
            "feature_comparisons": {},
            "matched_feature_count": 3,
            "total_feature_count": 4,
            "reason": "Test disagreement.",
        }

    def submit_deposit(self):
        return self.client.post(
            "/api/rag/evaluate",
            data={
                "label": "Diet Coke can",
                "reading_id": "TEST-READING-001",
                "wallet_address": self.WALLET,
                "bin_id": "BIN001",
            },
            files={
                "image": (
                    "test.png",
                    b"test-image-content",
                    "image/png",
                ),
            },
        )

    def test_real_reference_assessment_uses_saved_sensor_samples(self):
        raw_samples = [
            {"t_ms": 0, "weight_g": 30.0},
            {"t_ms": 500, "weight_g": 20.0},
            {"t_ms": 1000, "weight_g": 15.0},
            {"t_ms": 1500, "weight_g": 12.0},
            {"t_ms": 2500, "weight_g": 12.0},
            {"t_ms": 3500, "weight_g": 12.0},
            {"t_ms": 4500, "weight_g": 12.0},
            {"t_ms": 5500, "weight_g": 12.0},
            {"t_ms": 6500, "weight_g": 12.0},
            {"t_ms": 7500, "weight_g": 12.0},
        ]

        # Populate the same fields that the ESP32 measurement endpoint stores.
        db = self.TestSessionLocal()
        try:
            reading = (
                db.query(SensorReading)
                .filter_by(reading_id="TEST-READING-001")
                .one()
            )
            reading.baseline_mean_g = 0.0
            reading.impact_raw_samples = raw_samples
            reading.impact_sample_count = len(raw_samples)
            db.commit()
        finally:
            db.close()

        # Deliberately do not mock assess_mechanical_fingerprint.
        with (
            patch.object(
                deposit_route,
                "classify_image",
                return_value={
                    "label": "diet_coke",
                    "confidence": 0.99,
                },
            ),
            patch.object(
                deposit_route,
                "sensor_fusion",
                return_value=self.accepted_fusion_result(),
            ),
            patch.object(
                deposit_route,
                "calculate_reward",
                return_value=0.25,
            ),
            patch.object(
                deposit_route,
                "mint_recycling_reward",
                return_value={
                    "status": "SUCCESS",
                    "tx_hash": "0x" + ("d" * 64),
                },
            ),
        ):
            response = self.submit_deposit()

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["hardware_route_signal"], "M")

        assessment = body["mechanical_assessment"]
        self.assertEqual(assessment["status"], "SHADOW_ASSESSED")
        self.assertEqual(assessment["assessment_mode"], "SHADOW_ONLY")
        self.assertTrue(assessment["mechanical_agreement"])
        self.assertEqual(assessment["matched_feature_count"], 4)
        self.assertEqual(assessment["total_feature_count"], 4)
        self.assertEqual(assessment["persistence_status"], "SAVED")

        features = assessment["extracted_features"]
        self.assertAlmostEqual(features["peak_g"], 30.0, places=5)
        self.assertAlmostEqual(features["early_rms_g"], 19.042, places=2)
        self.assertAlmostEqual(features["area_g_seconds"], 100.0, places=5)
        self.assertAlmostEqual(features["stable_weight_g"], 14.4458, places=4)

        db = self.TestSessionLocal()
        try:
            saved = (
                db.query(MechanicalReferenceAssessment)
                .filter_by(reading_id="TEST-READING-001")
                .one()
            )

            self.assertEqual(saved.status, "SHADOW_ASSESSED")
            self.assertEqual(saved.assessment_mode, "SHADOW_ONLY")
            self.assertTrue(saved.mechanical_agreement)
            self.assertEqual(saved.matched_feature_count, 4)
            self.assertEqual(saved.total_feature_count, 4)
            self.assertAlmostEqual(saved.peak_g, 30.0, places=5)
            self.assertAlmostEqual(saved.area_g_seconds, 100.0, places=5)
            self.assertAlmostEqual(saved.stable_weight_g, 14.4458, places=4)
            self.assertEqual(len(saved.extracted_features), 4)
            self.assertEqual(len(saved.feature_comparisons), 4)
        finally:
            db.close()

    def test_mechanical_disagreement_does_not_change_deposit_or_route(self):
        with (
            patch.object(
                deposit_route,
                "classify_image",
                return_value={
                    "label": "diet_coke",
                    "confidence": 0.99,
                },
            ),
            patch.object(
                deposit_route,
                "assess_mechanical_fingerprint",
                return_value=self.assessment_disagrees_with_image(),
            ),
            patch.object(
                deposit_route,
                "sensor_fusion",
                return_value=self.accepted_fusion_result(),
            ),
            patch.object(
                deposit_route,
                "calculate_reward",
                return_value=0.25,
            ),
            patch.object(
                deposit_route,
                "mint_recycling_reward",
                return_value={
                    "status": "SUCCESS",
                    "tx_hash": "0x" + ("a" * 64),
                    "explorer_url": "https://example.com/tx/test",
                },
            ),
        ):
            response = self.submit_deposit()

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["hardware_route_signal"], "M")
        self.assertEqual(
            body["fusion_result"]["hardware_route_signal"],
            "M",
        )

        assessment = body["mechanical_assessment"]
        self.assertEqual(assessment["status"], "SHADOW_ASSESSED")
        self.assertEqual(assessment["assessment_mode"], "SHADOW_ONLY")
        self.assertFalse(assessment["mechanical_agreement"])
        self.assertEqual(assessment["matched_feature_count"], 3)
        self.assertEqual(assessment["total_feature_count"], 4)
        self.assertEqual(assessment["persistence_status"], "SAVED")

        db = self.TestSessionLocal()
        try:
            saved_deposit = db.query(Deposit).one()
            saved_assessment = db.query(MechanicalReferenceAssessment).one()
            command = db.query(SegregationCommand).one()
            reading = (
                db.query(SensorReading)
                .filter_by(reading_id="TEST-READING-001")
                .one()
            )

            self.assertEqual(saved_deposit.hardware_route_signal, "M")
            self.assertEqual(command.route_signal, "M")
            self.assertTrue(reading.consumed)
            self.assertEqual(
                saved_assessment.model_name,
                "item_specific_mechanical_reference",
            )
            self.assertEqual(
                saved_assessment.assessment_mode,
                "SHADOW_ONLY",
            )
            self.assertFalse(saved_assessment.mechanical_agreement)
            self.assertEqual(saved_assessment.matched_feature_count, 3)
            self.assertEqual(saved_assessment.total_feature_count, 4)
            self.assertEqual(
                saved_assessment.deposit_id,
                saved_deposit.id,
            )
        finally:
            db.close()

    def test_assessment_exception_does_not_fail_deposit(self):
        with (
            patch.object(
                deposit_route,
                "classify_image",
                return_value={
                    "label": "diet_coke",
                    "confidence": 0.99,
                },
            ),
            patch.object(
                deposit_route,
                "assess_mechanical_fingerprint",
                side_effect=RuntimeError("Simulated assessment failure"),
            ),
            patch.object(
                deposit_route,
                "sensor_fusion",
                return_value=self.accepted_fusion_result(),
            ),
            patch.object(
                deposit_route,
                "calculate_reward",
                return_value=0.25,
            ),
            patch.object(
                deposit_route,
                "mint_recycling_reward",
                return_value={
                    "status": "SUCCESS",
                    "tx_hash": "0x" + ("b" * 64),
                },
            ),
        ):
            response = self.submit_deposit()

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["hardware_route_signal"], "M")
        self.assertEqual(
            body["mechanical_assessment"]["status"],
            "ASSESSMENT_ERROR",
        )
        self.assertEqual(
            body["mechanical_assessment"]["persistence_status"],
            "SAVED",
        )

        db = self.TestSessionLocal()
        try:
            self.assertEqual(db.query(Deposit).count(), 1)
            self.assertEqual(db.query(MechanicalReferenceAssessment).count(), 1)
            saved_assessment = db.query(MechanicalReferenceAssessment).one()
            self.assertEqual(saved_assessment.status, "ASSESSMENT_ERROR")
            self.assertEqual(saved_assessment.assessment_mode, "SHADOW_ONLY")
        finally:
            db.close()

    def test_assessment_persistence_failure_does_not_fail_deposit(self):
        with (
            patch.object(
                deposit_route,
                "classify_image",
                return_value={
                    "label": "diet_coke",
                    "confidence": 0.99,
                },
            ),
            patch.object(
                deposit_route,
                "assess_mechanical_fingerprint",
                return_value=self.assessment_disagrees_with_image(),
            ),
            patch.object(
                deposit_route,
                "sensor_fusion",
                return_value=self.accepted_fusion_result(),
            ),
            patch.object(
                deposit_route,
                "calculate_reward",
                return_value=0.25,
            ),
            patch.object(
                deposit_route,
                "mint_recycling_reward",
                return_value={
                    "status": "SUCCESS",
                    "tx_hash": "0x" + ("c" * 64),
                },
            ),
            patch.object(
                deposit_route,
                "SessionLocal",
                side_effect=RuntimeError("Simulated database failure"),
            ),
        ):
            response = self.submit_deposit()

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["hardware_route_signal"], "M")
        self.assertEqual(
            body["mechanical_assessment"]["persistence_status"],
            "FAILED",
        )

        db = self.TestSessionLocal()
        try:
            self.assertEqual(db.query(Deposit).count(), 1)
            self.assertEqual(db.query(SegregationCommand).count(), 1)
            self.assertEqual(db.query(MechanicalReferenceAssessment).count(), 0)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
