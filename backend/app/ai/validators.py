"""
Pydantic validators for LLM-generated structured output.

All Groq responses MUST be validated through these models before
being used in application logic. Validation failures trigger a
single controlled retry attempt.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# Extraction validators
# ─────────────────────────────────────────────

class ExtractedComplaintFields(BaseModel):
    """Validated output of the extract_complaint LLM call."""
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

    @field_validator("*", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip().lower() in ("", "none", "null", "n/a", "not provided", "unknown"):
            return None
        return v


class LLMExtractionResponse(BaseModel):
    """Full validated response from the extraction LLM call."""
    complaint: ExtractedComplaintFields
    missing_fields: List[str] = Field(default_factory=list)
    confidence: Dict[str, float] = Field(default_factory=dict)

    @field_validator("missing_fields", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> Dict[str, float]:
        if not isinstance(v, dict):
            return {}
        # Clamp all values to [0, 1]
        return {k: max(0.0, min(1.0, float(val))) for k, val in v.items()}


# ─────────────────────────────────────────────
# Risk assessment validators
# ─────────────────────────────────────────────

class LLMRiskAssessmentResponse(BaseModel):
    """Validated output of the assess_risk LLM call."""
    category: str = Field(..., min_length=1)
    severity: Literal["Minor", "Major", "Critical"]
    priority: Literal["Low", "Medium", "High", "Critical"]
    rationale: str = Field(..., min_length=10)
    suggested_next_action: str = Field(..., min_length=10)

    @field_validator("category", "rationale", "suggested_next_action", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


# ─────────────────────────────────────────────
# Follow-up / correction validators
# ─────────────────────────────────────────────

VALID_COMPLAINT_FIELDS = {
    "complaint_source", "customer_name", "product_name", "strength_grade",
    "batch_lot_number", "manufacturing_date", "expiry_date", "quantity_affected",
    "complaint_type", "complaint_date", "description",
}

MATERIAL_FIELDS = {
    "batch_lot_number", "product_name", "complaint_type",
    "strength_grade", "quantity_affected", "description",
}


class LLMFollowUpResponse(BaseModel):
    """Validated output of the understand_followup LLM call."""
    field_updates: Dict[str, Any] = Field(default_factory=dict)
    is_material_change: bool = False
    clarification_needed: Optional[str] = None

    @field_validator("field_updates", mode="before")
    @classmethod
    def validate_field_names(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            return {}
        # Only allow known field names to prevent prompt injection
        return {k: val for k, val in v.items() if k in VALID_COMPLAINT_FIELDS}

    @model_validator(mode="after")
    def auto_detect_material_change(self) -> "LLMFollowUpResponse":
        """Override LLM material change flag if a material field was updated."""
        if any(field in MATERIAL_FIELDS for field in self.field_updates):
            self.is_material_change = True
        return self


# ─────────────────────────────────────────────
# Parse helpers
# ─────────────────────────────────────────────

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM output that may contain extra text/markdown.
    Returns parsed dict or raises ValueError.
    """
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract JSON block from markdown fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find first { ... } block
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM output: {text[:200]}")
