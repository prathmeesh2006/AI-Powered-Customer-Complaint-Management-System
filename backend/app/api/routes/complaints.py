"""
FastAPI route handlers for complaint intake workflow.

Route design:
- Each endpoint knows its input_type and sets it before calling LangGraph
- File parsing happens here (via document_parser) BEFORE the AI graph
- Business logic is delegated to complaint_service
- No DB write during AI analysis (draft-in-Redux)
- Only /commit writes to the database
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.schemas.complaint import (
    AnalysisResponse,
    AnalyzeTextRequest,
    CommitRequest,
    CommitResponse,
    ComplaintDetailResponse,
    ComplaintListItem,
    ErrorResponse,
    FollowUpRequest,
    FollowUpResponse,
)
from app.services.complaint_service import (
    commit_complaint,
    find_potential_duplicates,
    get_complaint_by_id,
    get_recent_complaints,
    run_complaint_analysis,
    run_followup,
)
from app.services.document_parser import parse_uploaded_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/complaints", tags=["complaints"])


# ─────────────────────────────────────────────
# POST /api/complaints/analyze-text
# ─────────────────────────────────────────────

@router.post("/analyze-text", response_model=AnalysisResponse)
def analyze_text(payload: AnalyzeTextRequest):
    """
    Analyze pasted complaint text or email.
    input_type="text" is set here — not by LLM classification.
    Returns structured analysis for Redux draft.
    """
    if not payload.text or len(payload.text.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Complaint text must be at least 10 characters.",
        )

    try:
        result = run_complaint_analysis(
            normalized_text=payload.text.strip(),
            input_type="text",  # explicitly set by this endpoint
        )
        return result
    except Exception as e:
        logger.error("analyze-text error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis failed: {str(e)}",
        )


# ─────────────────────────────────────────────
# POST /api/complaints/analyze-file
# ─────────────────────────────────────────────

MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/analyze-file", response_model=AnalysisResponse)
async def analyze_file(file: UploadFile = File(...)):
    """
    Upload and analyze a complaint document (PDF or text).
    
    File parsing happens here — normalized text is passed to LangGraph.
    input_type="document" is set by this endpoint.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    allowed_extensions = (".pdf", ".txt", ".text")
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=415,
            detail="Only PDF and plain text files are supported. Please upload a supported file or paste the complaint text.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB.",
        )
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Parse file → normalized text (file handling stays outside LangGraph)
    parse_result = parse_uploaded_file(
        file_bytes=file_bytes,
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
    )

    if not parse_result.success:
        raise HTTPException(
            status_code=422,
            detail=parse_result.error or "Could not parse the uploaded document.",
        )

    source_doc_meta = {
        "filename": parse_result.filename,
        "mime_type": parse_result.mime_type,
        "file_size_bytes": parse_result.file_size_bytes,
    }

    try:
        result = run_complaint_analysis(
            normalized_text=parse_result.text,
            input_type="document",  # explicitly set by this endpoint
            source_document=source_doc_meta,
        )
        return result
    except Exception as e:
        logger.error("analyze-file error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(e)}",
        )


# ─────────────────────────────────────────────
# POST /api/complaints/follow-up
# ─────────────────────────────────────────────

@router.post("/follow-up", response_model=FollowUpResponse)
def follow_up(payload: FollowUpRequest):
    """
    Process a conversational correction from the user.
    
    The current complaint state (from Redux draft) is passed in the request body.
    Only changed fields are returned. No DB write happens here.
    """
    try:
        result = run_followup(
            message=payload.message,
            current_complaint=payload.current_complaint.model_dump(),
            current_risk=payload.current_risk.model_dump() if payload.current_risk else None,
            session_id=payload.session_id,
        )
        return result
    except Exception as e:
        logger.error("follow-up error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Follow-up processing failed: {str(e)}",
        )


# ─────────────────────────────────────────────
# POST /api/complaints/new/commit
# Draft-in-Redux: no pre-existing DB record required
# ─────────────────────────────────────────────

@router.post("/new/commit", response_model=CommitResponse)
def commit_new(payload: CommitRequest, db: Session = Depends(get_db)):
    """
    Commit the reviewed complaint draft to the QMS Ledger.
    Called from the Redux draft — no pre-existing DB record required.
    This is the ONLY endpoint that writes to the database.
    Never reports success if the DB write fails.
    """
    try:
        result = commit_complaint(commit_data=payload, db=db)
        return result
    except Exception as e:
        logger.error("commit error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database commit failed: {str(e)}. Your complaint data is preserved — please retry.",
        )


@router.post("/{complaint_id}/commit", response_model=CommitResponse)
def commit(complaint_id: str, payload: CommitRequest, db: Session = Depends(get_db)):
    """Legacy commit endpoint with explicit complaint ID."""
    try:
        result = commit_complaint(commit_data=payload, db=db)
        return result
    except Exception as e:
        logger.error("commit error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database commit failed: {str(e)}. Your complaint data is preserved — please retry.",
        )


# ─────────────────────────────────────────────
# GET /api/complaints/{id}
# ─────────────────────────────────────────────

@router.get("/{complaint_id}", response_model=ComplaintDetailResponse)
def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    """Retrieve a committed complaint by ID."""
    complaint = get_complaint_by_id(complaint_id, db)
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found.")

    return ComplaintDetailResponse(
        id=complaint.id,
        complaint_source=complaint.complaint_source,
        customer_name=complaint.customer_name,
        product_name=complaint.product_name,
        strength_grade=complaint.strength_grade,
        batch_lot_number=complaint.batch_lot_number,
        manufacturing_date=complaint.manufacturing_date,
        expiry_date=complaint.expiry_date,
        quantity_affected=complaint.quantity_affected,
        complaint_type=complaint.complaint_type,
        complaint_date=complaint.complaint_date,
        description=complaint.description,
        severity=complaint.severity,
        priority=complaint.priority,
        risk_category=complaint.risk_category,
        risk_rationale=complaint.risk_rationale,
        suggested_next_action=complaint.suggested_next_action,
        status=complaint.status,
        missing_fields=complaint.missing_fields,
        source_filename=complaint.source_filename,
        created_at=complaint.created_at.isoformat() if complaint.created_at else None,
        committed_at=complaint.committed_at.isoformat() if complaint.committed_at else None,
    )


# ─────────────────────────────────────────────
# GET /api/complaints
# ─────────────────────────────────────────────

@router.get("", response_model=List[ComplaintListItem])
def list_complaints(limit: int = 20, db: Session = Depends(get_db)):
    """List recent committed complaints."""
    complaints = get_recent_complaints(db, limit=limit)
    return [
        ComplaintListItem(
            id=c.id,
            product_name=c.product_name,
            batch_lot_number=c.batch_lot_number,
            complaint_type=c.complaint_type,
            severity=c.severity,
            priority=c.priority,
            status=c.status,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in complaints
    ]


# ─────────────────────────────────────────────
# POST /api/complaints/check-duplicates
# ─────────────────────────────────────────────

@router.post("/check-duplicates")
def check_duplicates(
    product_name: Optional[str] = None,
    batch_lot_number: Optional[str] = None,
    complaint_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Find potentially duplicate complaints. Never auto-merges records."""
    candidates = find_potential_duplicates(
        product_name=product_name,
        batch_lot_number=batch_lot_number,
        complaint_type=complaint_type,
        db=db,
    )
    return {"candidates": candidates, "count": len(candidates)}
