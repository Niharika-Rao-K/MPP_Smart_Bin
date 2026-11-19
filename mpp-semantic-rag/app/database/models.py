from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from app.database.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    full_name = Column(
        String(255),
        nullable=True,
    )

    username = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    wallet_address = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class Bin(Base):
    __tablename__ = "bins"

    id = Column(Integer, primary_key=True, index=True)

    bin_code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    location = Column(
        String(255),
        nullable=True,
    )

    status = Column(
        String(20),
        default="ACTIVE",
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    deposits = relationship(
        "Deposit",
        back_populates="bin",
    )


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    transaction_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    bin_id = Column(
        Integer,
        ForeignKey("bins.id"),
        nullable=False,
    )

    wallet_address = Column(
        String(100),
        nullable=False,
    )

    predicted_label = Column(
        String(100),
        nullable=True,
    )

    confidence = Column(
        Float,
        nullable=True,
    )

    weight_g = Column(
        Float,
        nullable=True,
    )

    decision = Column(
        String(50),
        nullable=False,
    )

    hardware_route_signal = Column(
        String(5),
        nullable=True,
    )

    reward_amount = Column(
        Float,
        default=0.0,
    )

    reward_status = Column(
        String(30),
        default="SKIPPED",
    )

    tx_hash = Column(
        String(100),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    bin = relationship(
        "Bin",
        back_populates="deposits",
    )

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    bin_code = Column(String, index=True, nullable=False)
    sensor_id = Column(String, nullable=False)
    reading_id = Column(String, unique=True, index=True, nullable=False)
    weight_g = Column(Float, nullable=False)

    # Optional Mechanical Impact Fingerprinting indicators.
    impact_peak_g = Column(Float, nullable=True)
    impact_settling_ms = Column(Integer, nullable=True)
    impact_sample_count = Column(Integer, nullable=True)
    impact_variation_index = Column(Float, nullable=True)
    baseline_mean_g = Column(Float, nullable=True)
    impact_raw_samples = Column(JSON, nullable=True)

    consumed = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class MeasurementRequest(Base):
    __tablename__ = "measurement_requests"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    bin_code = Column(
        String(50),
        nullable=False,
        index=True,
    )

    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    claimed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )


class SegregationCommand(Base):
    __tablename__ = "segregation_commands"

    __table_args__ = (
        UniqueConstraint(
            "deposit_id",
            name="uq_segregation_command_deposit",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    command_id = Column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    deposit_id = Column(
        Integer,
        ForeignKey("deposits.id"),
        nullable=False,
    )

    bin_code = Column(
        String(50),
        nullable=False,
        index=True,
    )

    route_signal = Column(
        String(5),
        nullable=False,
    )

    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    claimed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )


class MechanicalReferenceAssessment(Base):
    """
    Stores exact-image-label mechanical reference comparisons.

    This is a direct experimental reference cross-check, not an ML model.
    Results remain shadow-only and do not control deposit decisions.
    """

    __tablename__ = "mechanical_reference_assessments"

    id = Column(Integer, primary_key=True, index=True)

    reading_id = Column(
        String,
        ForeignKey("sensor_readings.reading_id"),
        unique=True,
        nullable=False,
        index=True,
    )

    deposit_id = Column(
        Integer,
        ForeignKey("deposits.id"),
        nullable=True,
        index=True,
    )

    model_name = Column(String(100), nullable=False)
    model_version = Column(String(100), nullable=False)
    status = Column(String(40), nullable=False, index=True)
    assessment_mode = Column(String(30), nullable=False, default="SHADOW_ONLY")

    image_label = Column(String(100), nullable=False)
    image_expected_class = Column(String(50), nullable=True)
    mechanical_agreement = Column(Boolean, nullable=True)

    stable_weight_g = Column(Float, nullable=True)
    baseline_mean_g = Column(Float, nullable=True)
    impact_peak_g = Column(Float, nullable=True)
    impact_settling_ms = Column(Integer, nullable=True)
    impact_sample_count = Column(Integer, nullable=True)

    peak_g = Column(Float, nullable=True)
    early_rms_g = Column(Float, nullable=True)
    area_g_seconds = Column(Float, nullable=True)

    extracted_features = Column(JSON, nullable=True)
    feature_comparisons = Column(JSON, nullable=True)

    matched_feature_count = Column(Integer, nullable=True)
    total_feature_count = Column(Integer, nullable=True)

    reason = Column(String(500), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ImageFingerprint(Base):
    """Stores image fingerprints for previously rewarded deposits."""

    __tablename__ = "image_fingerprints"

    id = Column(Integer, primary_key=True, index=True)

    sha256 = Column(String(64), nullable=False, index=True)
    phash = Column(String(16), nullable=False, index=True)
    dhash = Column(String(16), nullable=True)

    wallet_address = Column(String(100), nullable=True, index=True)
    bin_code = Column(String(50), nullable=True)

    deposit_id = Column(
        Integer,
        ForeignKey("deposits.id"),
        nullable=True,
        index=True,
    )

    status = Column(
        String(10),
        default="accepted",
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
