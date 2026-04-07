"""
models.py — SQLAlchemy ORM models.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, Text, JSON, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base
import enum


class ClaimStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class ClaimType(str, enum.Enum):
    HEALTH = "health"
    AUTO = "auto"
    PROPERTY = "property"
    LIFE = "life"
    TRAVEL = "travel"


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    policy_number = Column(String(100), unique=True, index=True)
    is_admin = Column(Boolean, default=False)
    history_claim_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    claims = relationship("Claim", back_populates="user")


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Submission data
    claim_type = Column(SAEnum(ClaimType), nullable=False)
    description = Column(Text, nullable=False)
    requested_amount = Column(Float, nullable=False)
    incident_date = Column(DateTime(timezone=True))
    image_paths = Column(JSON, default=list)      # List of saved file paths

    # LLM-extracted fields
    extracted_data = Column(JSON, default=dict)   # Raw extraction result

    # AI Scores
    fraud_score = Column(Float)                   # 0=clean, 1=fraud
    anomaly_score = Column(Float)                 # Isolation Forest score
    image_valid = Column(Boolean)
    estimated_payout = Column(Float)
    payout_match_pct = Column(Float)              # 0-1

    # Decision
    status = Column(SAEnum(ClaimStatus), default=ClaimStatus.PENDING)
    decision_reason = Column(Text)
    settled_amount = Column(Float)

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), default=now_utc)
    processed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user = relationship("User", back_populates="claims")
    fraud_logs = relationship("FraudLog", back_populates="claim")


class FraudLog(Base):
    __tablename__ = "fraud_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    fraud_score = Column(Float, nullable=False)
    anomaly_score = Column(Float)
    feature_breakdown = Column(JSON)              # Per-feature importances
    flagged_rules = Column(JSON, default=list)    # Human-readable rule triggers
    created_at = Column(DateTime(timezone=True), default=now_utc)

    claim = relationship("Claim", back_populates="fraud_logs")


class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50))              # "claim" | "user"
    entity_id = Column(UUID(as_uuid=True))
    action = Column(String(100))
    actor = Column(String(255))
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=now_utc)
