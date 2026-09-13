"""
Complaint service — orchestrates between FastAPI routes, LangGraph graphs, and the database.

Key responsibilities:
- Run complaint_graph for new analysis
- Run followup_graph for corrections
- Persist committed complaints to the database
- Record audit events
- Avoid requiring a DB record during AI analysis (draft-in-Redux architecture)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.ai.graph import complaint_graph, followup_graph
from app.ai.state import ComplaintState
from app.models.complaint import Complaint, ComplaintAssessment, ComplaintEvent, SourceDocument
from app.schemas.complaint import (
    AnalysisResponse,
    CommitRequest,
    CommitResponse,
    ComplaintFieldsSchema,
    FollowUpResponse,
    RiskAssessmentSchema,
)
from app.config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────

def run_complaint_analysis(
    normalized_text: str,
    input_type: str,
    source_document: Optional[Dict[str, Any]] = None,
    existing_corrections: Optional[Dict[str, Any]] = None,
) -> AnalysisResponse:
    """
    Run the complaint analysis LangGraph workflow.
    
    input_type is set by the FastAPI endpoint — not determined by LLM.
    Document parsing already completed before this function is called.
    Returns a structured response for the Redux draft — no DB write here.
    """
    initial_state: ComplaintState = {
        "input_type": input_type,
        "raw_input": normalized_text,
        "normalized_text": normalized_text,
        "source_document": source_document,
        "complaint": {},
        "user_corrections": existing_corrections or {},
        "missing_fields": [],
        "confidence": {},
        "risk_assessment": {},
        "messages": [],
        "workflow_status": "starting",
        "errors": [],
        "retry_count": 0,
        "material_change": False,
        "field_updates": {},
    }

    logger.info("Starting complaint analysis graph. input_type=%s", input_type)
    final_state: ComplaintState = complaint_graph.invoke(initial_state)

    complaint = final_state.get("complaint", {})
    risk = final_state.get("risk_assessment", {}) or {}
    messages = final_state.get("messages", [])
    copilot_message = messages[-1]["content"] if messages else "Analysis complete. Please review."

    return AnalysisResponse(
        complaint=ComplaintFieldsSchema(**complaint),
        risk=RiskAssessmentSchema(**risk) if risk else RiskAssessmentSchema(),
        missing_fields=final_state.get("missing_fields", []),
        confidence=final_state.get("confidence", {}),
        copilot_message=copilot_message,
        workflow_status=final_state.get("workflow_status", "complete"),
        source_filename=source_document.get("filename") if source_document else None,
    )


def run_followup(
    message: str,
    current_complaint: Dict[str, Any],
    current_risk: Optional[Dict[str, Any]],
    session_id: Optional[str] = None,
) -> FollowUpResponse:
    """
    Run the follow-up correction LangGraph workflow.
    
    The current complaint state from Redux is passed as context.
    Returns only the changed fields plus the full merged state.
    """
    initial_state: ComplaintState = {
        "input_type": "followup",
        "raw_input": message,
        "normalized_text": message,
        "source_document": None,
        "complaint": current_complaint,
        "user_corrections": {},
        "missing_fields": [],
        "confidence": {},
        "risk_assessment": current_risk or {},
        "messages": [],
        "followup_message": message,
        "field_updates": {},
        "material_change": False,
        "workflow_status": "starting",
        "errors": [],
        "retry_count": 0,
    }

    logger.info("Starting follow-up graph for message: %s", message[:100])
    final_state: ComplaintState = followup_graph.invoke(initial_state)

    field_updates = final_state.get("field_updates", {})
    updated_complaint = final_state.get("complaint", current_complaint)
    updated_risk = final_state.get("risk_assessment", current_risk) or {}
    messages = final_state.get("messages", [])
    copilot_message = messages[-1]["content"] if messages else "Updated."
    clarification = final_state.get("_clarification_needed")
    risk_reassessed = final_state.get("_risk_reassessed", False)

    return FollowUpResponse(
        updated_fields=field_updates,
        complaint=ComplaintFieldsSchema(**updated_complaint),
        risk=RiskAssessmentSchema(**updated_risk) if updated_risk else None,
        risk_reassessed=risk_reassessed,
        copilot_message=copilot_message,
        missing_fields=final_state.get("missing_fields", []),
        clarification_needed=clarification,
    )


# ─────────────────────────────────────────────
# QMS Ledger commit (only database write)
# ─────────────────────────────────────────────

def commit_complaint(commit_data: CommitRequest, db: Session) -> CommitResponse:
    """
    Persist the reviewed complaint to the database.
    
    This is the ONLY place where a database record is created (draft-in-Redux architecture).
    Records an audit event for each committed field and the AI assessment.
    Returns failure if the DB write fails — never claim success on error.
    """
    complaint_dict = commit_data.complaint.model_dump()
    risk_dict = commit_data.risk.model_dump() if commit_data.risk else {}

    now = datetime.now(timezone.utc)

    # Create complaint record
    db_complaint = Complaint(
        **{k: v for k, v in complaint_dict.items() if v is not None},
        severity=risk_dict.get("severity"),
        priority=risk_dict.get("priority"),
        risk_category=risk_dict.get("category"),
        risk_rationale=risk_dict.get("rationale"),
        suggested_next_action=risk_dict.get("suggested_next_action"),
        status="committed",
        missing_fields=commit_data.missing_fields,
        confidence=commit_data.confidence,
        source_filename=commit_data.source_filename,
        committed_at=now,
    )
    db.add(db_complaint)
    db.flush()  # get the ID without committing yet

    # Record AI assessment
    if risk_dict:
        assessment = ComplaintAssessment(
            complaint_id=db_complaint.id,
            category=risk_dict.get("category"),
            severity=risk_dict.get("severity"),
            priority=risk_dict.get("priority"),
            rationale=risk_dict.get("rationale"),
            suggested_action=risk_dict.get("suggested_next_action"),
            groq_model=settings.groq_model,
        )
        db.add(assessment)

    # Record commit event
    db.add(ComplaintEvent(
        complaint_id=db_complaint.id,
        event_type="commit",
        field_name=None,
        old_value=None,
        new_value="committed",
        actor="user",
    ))

    db.commit()
    db.refresh(db_complaint)

    logger.info("Complaint committed to QMS Ledger: %s", db_complaint.id)

    return CommitResponse(
        complaint_id=db_complaint.id,
        status="committed",
        message="Complaint committed to QMS Ledger successfully.",
        committed_at=now.isoformat(),
    )


def record_correction_event(
    complaint_id: str,
    field_name: str,
    old_value: Any,
    new_value: Any,
    actor: str,
    db: Session,
) -> None:
    """Record a field correction in the audit trail."""
    db.add(ComplaintEvent(
        complaint_id=complaint_id,
        event_type="field_correction",
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        actor=actor,
    ))
    db.commit()


def get_recent_complaints(db: Session, limit: int = 20) -> List[Complaint]:
    """Retrieve recent complaints for the history view."""
    return (
        db.query(Complaint)
        .order_by(Complaint.created_at.desc())
        .limit(limit)
        .all()
    )


def get_complaint_by_id(complaint_id: str, db: Session) -> Optional[Complaint]:
    return db.query(Complaint).filter(Complaint.id == complaint_id).first()


def find_potential_duplicates(
    product_name: Optional[str],
    batch_lot_number: Optional[str],
    complaint_type: Optional[str],
    db: Session,
    days: int = 90,
) -> List[Dict[str, Any]]:
    """
    Find potentially duplicate complaints by product + batch + type.
    Returns candidates with similarity reason — never auto-merges.
    """
    from sqlalchemy import and_, func
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    candidates = []

    query = db.query(Complaint).filter(Complaint.created_at >= cutoff)

    if batch_lot_number and product_name:
        matches = query.filter(
            Complaint.batch_lot_number == batch_lot_number,
            Complaint.product_name == product_name,
        ).all()
        for m in matches:
            candidates.append({
                "id": m.id,
                "product_name": m.product_name,
                "batch_lot_number": m.batch_lot_number,
                "complaint_type": m.complaint_type,
                "severity": m.severity,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "similarity_reason": "Same product and batch/lot number",
            })

    elif product_name and complaint_type:
        matches = query.filter(
            Complaint.product_name == product_name,
            Complaint.complaint_type == complaint_type,
        ).all()
        for m in matches:
            if not any(c["id"] == m.id for c in candidates):
                candidates.append({
                    "id": m.id,
                    "product_name": m.product_name,
                    "batch_lot_number": m.batch_lot_number,
                    "complaint_type": m.complaint_type,
                    "severity": m.severity,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "similarity_reason": "Same product and complaint type",
                })

    return candidates[:5]  # cap at 5 candidates
