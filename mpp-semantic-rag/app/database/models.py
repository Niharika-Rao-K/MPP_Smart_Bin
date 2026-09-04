from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
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
