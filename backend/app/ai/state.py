"""
LangGraph runtime state — uses TypedDict for efficient graph state passing.

Pydantic models for domain logic live in schemas/ and ai/validators.py.
This TypedDict is the shared mutable state threaded through every graph node.
"""
from typing import Any, Dict, List, Optional, TypedDict


class ComplaintData(TypedDict, total=False):
    complaint_source: Optional[str]
    customer_name: Optional[str]
    product_name: Optional[str]
    strength_grade: Optional[str]
    batch_lot_number: Optional[str]
    manufacturing_date: Optional[str]
    expiry_date: Optional[str]
    quantity_affected: Optional[str]
    complaint_type: Optional[str]
    complaint_date: Optional[str]
    description: Optional[str]


class RiskData(TypedDict, total=False):
    category: Optional[str]
    severity: Optional[str]
    priority: Optional[str]
    rationale: Optional[str]
    suggested_next_action: Optional[str]


class ComplaintState(TypedDict, total=False):
    # Set by FastAPI before entering the graph — never determined by classify_input LLM call
    input_type: str          # "text" | "document" | "followup"
    raw_input: str           # original complaint text
    normalized_text: str     # parsed/cleaned text ready for LLM
    source_document: Optional[Dict[str, Any]]  # filename, mime_type, size

    # Core complaint data
    complaint: ComplaintData
    user_corrections: Dict[str, Any]   # fields explicitly set by user (highest priority)
    missing_fields: List[str]
    confidence: Dict[str, float]

    # Follow-up specific
    followup_message: Optional[str]
    field_updates: Dict[str, Any]      # parsed field changes from follow-up
    material_change: bool              # whether reassessment is warranted

    # Risk assessment
    risk_assessment: RiskData

    # Copilot output
    messages: List[Dict[str, str]]    # [{role, content}]

    # Workflow
    workflow_status: str
    errors: List[str]
    retry_count: int
