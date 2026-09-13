"""
SQLAlchemy ORM models for AIVOA complaint management.

Tables:
- complaints           → finalized QMS complaint record
- complaint_assessments→ AI risk assessment history
- complaint_events     → audit trail (corrections, status changes)
- source_documents     → uploaded file metadata
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    # Origin & Customer
    complaint_source: Mapped[Optional[str]] = mapped_column(String(100))
    customer_name: Mapped[Optional[str]] = mapped_column(String(200))
    # Product & Batch
    product_name: Mapped[Optional[str]] = mapped_column(String(200))
    strength_grade: Mapped[Optional[str]] = mapped_column(String(100))
    batch_lot_number: Mapped[Optional[str]] = mapped_column(String(100))
    manufacturing_date: Mapped[Optional[str]] = mapped_column(String(50))
    expiry_date: Mapped[Optional[str]] = mapped_column(String(50))
    quantity_affected: Mapped[Optional[str]] = mapped_column(String(100))
    # Complaint details
    complaint_type: Mapped[Optional[str]] = mapped_column(String(100))
    complaint_date: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    # AI Risk Assessment (denormalized for quick access)
    severity: Mapped[Optional[str]] = mapped_column(String(20))
    priority: Mapped[Optional[str]] = mapped_column(String(20))
    risk_category: Mapped[Optional[str]] = mapped_column(String(100))
    risk_rationale: Mapped[Optional[str]] = mapped_column(Text)
    suggested_next_action: Mapped[Optional[str]] = mapped_column(Text)
    # Metadata
    status: Mapped[str] = mapped_column(String(30), default="draft")
    missing_fields: Mapped[Optional[list]] = mapped_column(JSON)
    confidence: Mapped[Optional[dict]] = mapped_column(JSON)
    source_filename: Mapped[Optional[str]] = mapped_column(String(500))
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    committed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    assessments: Mapped[List["ComplaintAssessment"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )
    events: Mapped[List["ComplaintEvent"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )
    source_documents: Mapped[List["SourceDocument"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )


class ComplaintAssessment(Base):
    """Stores each AI risk assessment (multiple per complaint are possible after corrections)."""

    __tablename__ = "complaint_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    complaint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("complaints.id"), nullable=False
    )
    category: Mapped[Optional[str]] = mapped_column(String(100))
    severity: Mapped[Optional[str]] = mapped_column(String(20))
    priority: Mapped[Optional[str]] = mapped_column(String(20))
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    suggested_action: Mapped[Optional[str]] = mapped_column(Text)
    groq_model: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    complaint: Mapped["Complaint"] = relationship(back_populates="assessments")


class ComplaintEvent(Base):
    """Audit trail for every field correction and status change."""

    __tablename__ = "complaint_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    complaint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("complaints.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50))  # e.g. "field_correction", "status_change", "ai_assessment"
    field_name: Mapped[Optional[str]] = mapped_column(String(100))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(50), default="user")  # "user" or "ai"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    complaint: Mapped["Complaint"] = relationship(back_populates="events")


class SourceDocument(Base):
    """Uploaded complaint document metadata."""

    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    complaint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("complaints.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    complaint: Mapped["Complaint"] = relationship(back_populates="source_documents")
