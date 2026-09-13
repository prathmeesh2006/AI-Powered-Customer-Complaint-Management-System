"""
LangGraph nodes for the AIVOA complaint intake workflow.

Architecture decisions (from architectural corrections):
- input_type is set by FastAPI before entering the graph — no LLM-based classification
- File parsing happens in document_parser.py BEFORE the graph runs
- Groq output is strictly validated with Pydantic; one controlled retry on failure
- User corrections take priority over AI extractions (merge_state)
- Material field changes trigger reassessment; trivial messages do not
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from groq import Groq, APIError, APITimeoutError

from app.ai.state import ComplaintState
from app.ai.prompts import (
    SYSTEM_PROMPT,
    EXTRACTION_PROMPT_TEMPLATE,
    RISK_ASSESSMENT_PROMPT_TEMPLATE,
    FOLLOWUP_PROMPT_TEMPLATE,
    COPILOT_RESPONSE_PROMPT_TEMPLATE,
)
from app.ai.validators import (
    LLMExtractionResponse,
    LLMRiskAssessmentResponse,
    LLMFollowUpResponse,
    MATERIAL_FIELDS,
    extract_json_from_text,
)
from app.config import settings

logger = logging.getLogger(__name__)


def _get_groq_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


FALLBACK_MODELS = ["qwen/qwen3.8-27b", "groq/compound-mini", "groq/compound", "openai/gpt-oss-20b"]


_UNAVAILABLE_MODELS: set[str] = set()


def _call_groq(
    client: Groq,
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
) -> str:
    """Make a Groq API call and return the raw text content."""
    models_to_try = [settings.groq_model]
    for m in FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_name in models_to_try:
        if model_name in _UNAVAILABLE_MODELS:
            continue
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=2048,
                response_format={"type": "json_object"},  # enforce JSON output
                timeout=settings.groq_timeout,
            )
            return response.choices[0].message.content or ""
        except Exception as err:
            last_error = err
            err_msg = str(err).lower()
            if "model_not_found" in err_msg or "decommissioned" in err_msg or "404" in err_msg or "400" in err_msg or "not exist" in err_msg or "not found" in err_msg or "timeout" in err_msg:
                logger.warning("Groq model '%s' unavailable (%s). Marking unavailable and trying fallback...", model_name, err)
                _UNAVAILABLE_MODELS.add(model_name)
                continue
            raise err

    if last_error:
        raise last_error
    raise RuntimeError("No Groq model succeeded")


# ─────────────────────────────────────────────
# Node 1: extract_complaint
# ─────────────────────────────────────────────

def extract_complaint(state: ComplaintState) -> ComplaintState:
    """
    Use Groq LLM to extract structured complaint fields from normalized_text.
    Validates output with Pydantic. Retries once on validation failure.
    Never trusts raw LLM text for application state.
    """
    text = state.get("normalized_text", "") or state.get("raw_input", "")
    if not text:
        return {
            **state,
            "workflow_status": "error",
            "errors": state.get("errors", []) + ["No complaint text to extract from"],
        }

    client = _get_groq_client()
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(complaint_text=text)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    raw_output = ""
    for attempt in range(2):  # one retry on validation failure
        try:
            raw_output = _call_groq(client, messages)
            parsed = extract_json_from_text(raw_output)
            validated = LLMExtractionResponse.model_validate(parsed)

            # Merge with any existing user corrections (user corrections take priority)
            extracted_fields = validated.complaint.model_dump()
            user_corrections = state.get("user_corrections", {})
            merged = {**extracted_fields, **user_corrections}

            logger.info("Extraction successful on attempt %d", attempt + 1)
            return {
                **state,
                "complaint": merged,
                "missing_fields": validated.missing_fields,
                "confidence": validated.confidence,
                "workflow_status": "extracted",
                "retry_count": attempt,
                "errors": [],
            }

        except Exception as e:
            logger.warning("Extraction attempt %d failed: %s", attempt + 1, str(e))
            if attempt == 0:
                # Add repair instruction and retry
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({
                    "role": "user",
                    "content": (
                        "Your response was not valid JSON matching the required schema. "
                        "Please return ONLY the JSON object with no other text. "
                        "Do not include any explanation before or after the JSON."
                    ),
                })
            else:
                return {
                    **state,
                    "workflow_status": "extraction_failed",
                    "errors": state.get("errors", []) + [
                        f"Could not parse AI extraction response after retry: {str(e)}"
                    ],
                }

    return state  # unreachable but satisfies type checker


# ─────────────────────────────────────────────
# Node 2: validate_fields
# ─────────────────────────────────────────────

REQUIRED_FIELDS = {"product_name", "batch_lot_number", "complaint_type"}
PREFERRED_FIELDS = {
    "customer_name", "strength_grade", "manufacturing_date",
    "expiry_date", "quantity_affected", "complaint_date", "complaint_source",
}


def validate_fields(state: ComplaintState) -> ComplaintState:
    """
    Validate extracted complaint data.
    Detects missing required and preferred fields.
    Does NOT hallucinate values for missing fields.
    """
    complaint = state.get("complaint", {})
    current_missing = set(state.get("missing_fields", []))

    for field in REQUIRED_FIELDS:
        val = complaint.get(field)
        if not val or (isinstance(val, str) and val.strip() == ""):
            current_missing.add(field)

    # Notify if preferred fields are absent
    for field in PREFERRED_FIELDS:
        val = complaint.get(field)
        if not val or (isinstance(val, str) and val.strip() == ""):
            if field not in current_missing:
                current_missing.add(field)

    logger.info("Validation complete. Missing fields: %s", list(current_missing))
    return {
        **state,
        "missing_fields": list(current_missing),
        "workflow_status": "validated",
    }


# ─────────────────────────────────────────────
# Node 3: assess_risk
# ─────────────────────────────────────────────

def assess_risk(state: ComplaintState) -> ComplaintState:
    """
    Use Groq LLM to generate an initial risk assessment.
    Validates with Pydantic. One controlled retry on failure.
    """
    complaint = state.get("complaint", {})
    if not complaint:
        return {
            **state,
            "workflow_status": "risk_skipped",
            "errors": state.get("errors", []) + ["No complaint data for risk assessment"],
        }

    client = _get_groq_client()
    complaint_json = json.dumps(complaint, indent=2, default=str)
    prompt = RISK_ASSESSMENT_PROMPT_TEMPLATE.format(complaint_json=complaint_json)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    raw_output = ""
    for attempt in range(2):
        try:
            raw_output = _call_groq(client, messages)
            parsed = extract_json_from_text(raw_output)
            validated = LLMRiskAssessmentResponse.model_validate(parsed)

            risk = {
                "category": validated.category,
                "severity": validated.severity,
                "priority": validated.priority,
                "rationale": validated.rationale,
                "suggested_next_action": validated.suggested_next_action,
            }

            logger.info("Risk assessment complete: %s/%s", risk["severity"], risk["priority"])
            return {
                **state,
                "risk_assessment": risk,
                "workflow_status": "risk_assessed",
                "errors": [],
            }

        except Exception as e:
            logger.warning("Risk assessment attempt %d failed: %s", attempt + 1, str(e))
            if attempt == 0:
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({
                    "role": "user",
                    "content": (
                        "Your response was not valid JSON. "
                        "Return ONLY the JSON object with severity as exactly one of: Minor, Major, Critical "
                        "and priority as exactly one of: Low, Medium, High, Critical."
                    ),
                })
            else:
                return {
                    **state,
                    "risk_assessment": None,
                    "workflow_status": "risk_failed",
                    "errors": state.get("errors", []) + [
                        f"Could not parse risk assessment after retry: {str(e)}"
                    ],
                }

    return state


# ─────────────────────────────────────────────
# Node 4: build_copilot_response
# ─────────────────────────────────────────────

def build_copilot_response(state: ComplaintState) -> ComplaintState:
    """
    Generate a human-readable copilot message explaining:
    - what was extracted
    - what is missing
    - the risk assessment
    - suggested next action
    
    Uses a simple template approach for reliability rather than another LLM call.
    """
    complaint = state.get("complaint", {})
    risk = state.get("risk_assessment", {}) or {}
    missing = state.get("missing_fields", [])
    status = state.get("workflow_status", "")
    input_type = state.get("input_type", "text")

    # Build a clear, professional message
    parts = []

    if status == "extraction_failed":
        message = (
            "I was unable to extract complaint details from the provided input. "
            "Please check that the text contains complaint information and try again, "
            "or paste the complaint text directly."
        )
    else:
        source_desc = "document" if input_type == "document" else "complaint text"
        product = complaint.get("product_name", "the product")
        batch = complaint.get("batch_lot_number")
        ctype = complaint.get("complaint_type")

        # Opening: what was extracted
        parts.append(
            f"I've analyzed the {source_desc} and extracted the complaint details."
        )

        if product and batch and ctype:
            parts.append(
                f"This appears to be a **{ctype}** complaint for **{product}** "
                f"(Batch: {batch})."
            )
        elif product:
            parts.append(f"Complaint involves **{product}**.")

        # Missing fields
        critical_missing = [f for f in missing if f in {"batch_lot_number", "product_name", "complaint_type"}]
        if critical_missing:
            field_labels = {
                "batch_lot_number": "Batch/Lot Number",
                "product_name": "Product Name",
                "complaint_type": "Complaint Type",
            }
            labels = [field_labels.get(f, f.replace("_", " ").title()) for f in critical_missing]
            parts.append(
                f"⚠️ Key traceability fields are missing: **{', '.join(labels)}**. "
                "Please provide these before committing."
            )
        elif missing:
            count = len(missing)
            parts.append(
                f"{count} optional field{'s' if count > 1 else ''} could not be confirmed — "
                "review the highlighted fields."
            )

        # Risk summary
        if risk:
            sev = risk.get("severity", "")
            pri = risk.get("priority", "")
            action = risk.get("suggested_next_action", "")
            if sev and pri:
                parts.append(
                    f"Initial AI risk assessment: **{sev}** severity, **{pri}** priority."
                )
            if action:
                parts.append(f"Suggested action: {action}")

        parts.append(
            "Please review all extracted fields, make any corrections, "
            "then commit to the QMS Ledger when ready."
        )

        message = " ".join(parts)

    existing_messages = state.get("messages", [])
    new_messages = existing_messages + [{"role": "assistant", "content": message}]

    return {
        **state,
        "messages": new_messages,
        "workflow_status": "complete",
    }


# ─────────────────────────────────────────────
# Follow-up nodes
# ─────────────────────────────────────────────

def understand_followup(state: ComplaintState) -> ComplaintState:
    """
    Parse a user correction message and extract field updates.
    User corrections are treated as authoritative.
    Material field changes are auto-detected by the validator.
    """
    message = state.get("followup_message", "")
    current_complaint = state.get("complaint", {})

    if not message:
        return {
            **state,
            "field_updates": {},
            "material_change": False,
            "workflow_status": "followup_no_message",
        }

    client = _get_groq_client()
    complaint_json = json.dumps(current_complaint, indent=2, default=str)
    prompt = FOLLOWUP_PROMPT_TEMPLATE.format(
        current_complaint_json=complaint_json,
        user_message=message,
    )
    messages_payload = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    raw_output = ""
    for attempt in range(2):
        try:
            raw_output = _call_groq(client, messages_payload)
            parsed = extract_json_from_text(raw_output)
            validated = LLMFollowUpResponse.model_validate(parsed)

            logger.info(
                "Follow-up parsed. Updates: %s, Material: %s",
                list(validated.field_updates.keys()),
                validated.is_material_change,
            )
            return {
                **state,
                "field_updates": validated.field_updates,
                "material_change": validated.is_material_change,
                "workflow_status": "followup_parsed",
                "messages": state.get("messages", []) + [
                    {"role": "user", "content": message}
                ],
                # Store clarification if needed
                "_clarification_needed": validated.clarification_needed,
            }

        except Exception as e:
            logger.warning("Follow-up parse attempt %d failed: %s", attempt + 1, str(e))
            if attempt == 0:
                messages_payload.append({"role": "assistant", "content": raw_output})
                messages_payload.append({
                    "role": "user",
                    "content": (
                        "Return ONLY the JSON object. field_updates must contain only valid field names."
                    ),
                })
            else:
                return {
                    **state,
                    "field_updates": {},
                    "material_change": False,
                    "workflow_status": "followup_parse_failed",
                    "errors": state.get("errors", []) + [
                        f"Could not understand follow-up message: {str(e)}"
                    ],
                }

    return state


def merge_state(state: ComplaintState) -> ComplaintState:
    """
    Apply user-confirmed field updates to the complaint state.
    User corrections take priority over previous AI extractions.
    Records each changed field for audit purposes.
    """
    field_updates = state.get("field_updates", {})
    current_complaint = state.get("complaint", {})
    user_corrections = state.get("user_corrections", {})

    if not field_updates:
        return {**state, "workflow_status": "merged_no_changes"}

    # Track what changed for the response message and audit
    changes = {}
    for field, new_value in field_updates.items():
        old_value = current_complaint.get(field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}

    # Merge: user corrections always win
    updated_complaint = {**current_complaint, **field_updates}
    updated_user_corrections = {**user_corrections, **field_updates}

    logger.info("State merged. Changed fields: %s", list(changes.keys()))
    return {
        **state,
        "complaint": updated_complaint,
        "user_corrections": updated_user_corrections,
        "_field_changes": changes,  # used by build_correction_response
        "workflow_status": "merged",
    }


def reassess_if_needed(state: ComplaintState) -> ComplaintState:
    """
    Run assess_risk only if the follow-up involved material complaint changes.
    Trivial messages (confirmations, questions) do not trigger expensive re-assessment.
    """
    if state.get("material_change", False):
        logger.info("Material change detected — running risk reassessment")
        state = assess_risk(state)
        state["_risk_reassessed"] = True
    else:
        logger.info("No material change — skipping risk reassessment")
        state["_risk_reassessed"] = False
    return state


def build_correction_response(state: ComplaintState) -> ComplaintState:
    """
    Generate a confirmation message for conversational corrections.
    """
    changes = state.get("_field_changes", {})
    clarification = state.get("_clarification_needed")
    risk_reassessed = state.get("_risk_reassessed", False)
    risk = state.get("risk_assessment", {}) or {}

    if clarification:
        message = clarification
    elif not changes:
        message = (
            "I didn't detect any field updates in your message. "
            "Could you clarify which field you'd like to update? "
            "For example: 'The batch number is BMX240602' or 'The quantity is 48 capsules'."
        )
    else:
        # Build field label map
        field_labels = {
            "complaint_source": "Complaint Source",
            "customer_name": "Customer Name",
            "product_name": "Product Name",
            "strength_grade": "Strength/Grade",
            "batch_lot_number": "Batch/Lot Number",
            "manufacturing_date": "Manufacturing Date",
            "expiry_date": "Expiry Date",
            "quantity_affected": "Affected Quantity",
            "complaint_type": "Complaint Type",
            "complaint_date": "Complaint Date",
            "description": "Description",
        }

        update_parts = []
        for field, change in changes.items():
            label = field_labels.get(field, field.replace("_", " ").title())
            update_parts.append(f"**{label}** → {change['new']}")

        updates_str = ", ".join(update_parts)
        message = f"Got it. I've updated {updates_str}."

        if risk_reassessed and risk:
            sev = risk.get("severity", "")
            pri = risk.get("priority", "")
            if sev and pri:
                message += (
                    f" I also refreshed the initial risk assessment because the complaint record changed "
                    f"({sev} severity, {pri} priority)."
                )

        message += " Please review the updated fields and commit when ready."

    existing_messages = state.get("messages", [])
    return {
        **state,
        "messages": existing_messages + [{"role": "assistant", "content": message}],
        "workflow_status": "complete",
    }
