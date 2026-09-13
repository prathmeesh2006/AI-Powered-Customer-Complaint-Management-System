"""
Pydantic schemas for API request/response contracts.

These schemas define the API surface. LLM validation schemas live in ai/validators.py.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Shared sub-schemas
# ─────────────────────────────────────────────

class ComplaintFieldsSchema(BaseModel):
    """Structured complaint record — all fields optional because AI may not extract everything."""
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    strength_grade: Optional[str] = None
    batch_lot_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity_affected: Optional[str] = None
    complaint_type: Optional[str] = None
    complaint_date: Optional[str] = None
    description: Optional[str] = None


class RiskAssessmentSchema(BaseModel):
    """AI risk assessment result."""
    category: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    rationale: Optional[str] = None
    suggested_next_action: Optional[str] = None


# ─────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────

class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Complaint text or email body")
    session_id: Optional[str] = None


class FollowUpRequest(BaseModel):
    message: str = Field(..., min_length=1)
    current_complaint: ComplaintFieldsSchema = Field(
        ..., description="Current complaint state from Redux draft"
    )
    current_risk: Optional[RiskAssessmentSchema] = None
    session_id: Optional[str] = None


class CommitRequest(BaseModel):
    """Final complaint state sent for database persistence."""
    complaint: ComplaintFieldsSchema
    risk: Optional[RiskAssessmentSchema] = None
    missing_fields: List[str] = Field(default_factory=list)
    confidence: Dict[str, float] = Field(default_factory=dict)
    source_filename: Optional[str] = None


# ─────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────

class AnalysisResponse(BaseModel):
    """Returned after text or file analysis — populates Redux draft."""
    complaint: ComplaintFieldsSchema
    risk: RiskAssessmentSchema
    missing_fields: List[str] = Field(default_factory=list)
    confidence: Dict[str, float] = Field(default_factory=dict)
    copilot_message: str
    workflow_status: str = "complete"
    source_filename: Optional[str] = None


class FollowUpResponse(BaseModel):
    """Returned after a conversational correction."""
    updated_fields: Dict[str, Any]   # only changed fields
    complaint: ComplaintFieldsSchema  # full merged complaint state
    risk: Optional[RiskAssessmentSchema] = None
    risk_reassessed: bool = False
    copilot_message: str
    missing_fields: List[str] = Field(default_factory=list)
    clarification_needed: Optional[str] = None


class CommitResponse(BaseModel):
    complaint_id: str
    status: str = "committed"
    message: str = "Complaint committed to QMS Ledger successfully."
    committed_at: Optional[str] = None


class ComplaintDetailResponse(BaseModel):
    id: str
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    strength_grade: Optional[str] = None
    batch_lot_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity_affected: Optional[str] = None
    complaint_type: Optional[str] = None
    complaint_date: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    risk_category: Optional[str] = None
    risk_rationale: Optional[str] = None
    suggested_next_action: Optional[str] = None
    status: str = "draft"
    missing_fields: Optional[List[str]] = None
    source_filename: Optional[str] = None
    created_at: Optional[str] = None
    committed_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ComplaintListItem(BaseModel):
    id: str
    product_name: Optional[str] = None
    batch_lot_number: Optional[str] = None
    complaint_type: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    status: str
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    model: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
