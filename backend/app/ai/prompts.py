"""
LLM prompts for the AIVOA complaint intake AI workflow.

Prompts are structured to:
1. Return ONLY valid JSON (no prose wrappers)
2. Never invent missing data
3. Stay in the pharmaceutical QMS context
"""

# ─────────────────────────────────────────────
# System prompt (shared context)
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI assistant integrated into a pharmaceutical Quality Management System (QMS). 
Your role is to help complaint intake operators extract structured information from customer complaint texts and documents.

CRITICAL RULES — you MUST follow these without exception:
1. Return ONLY valid JSON. No explanation, no markdown, no prose outside the JSON.
2. NEVER invent batch numbers, dates, customer names, quantities, product names, or expiry dates.
3. If a field is not clearly stated in the complaint text, return null for that field.
4. You are NOT a final QA authority. Your assessments are initial recommendations only.
5. Preserve the exact wording of batch numbers, dates, and product names as they appear in the source."""


# ─────────────────────────────────────────────
# Extraction prompt
# ─────────────────────────────────────────────

EXTRACTION_PROMPT_TEMPLATE = """Extract structured complaint information from the following pharmaceutical complaint text.

COMPLAINT TEXT:
{complaint_text}

Return ONLY this JSON structure with no additional text:
{{
  "complaint": {{
    "complaint_source": "string or null (examples: Pharmacy, Email, Customer, Distributor, Regulatory Authority)",
    "customer_name": "string or null",
    "product_name": "string or null",
    "strength_grade": "string or null (e.g. 500 mg, Grade A)",
    "batch_lot_number": "string or null — copy exactly as written",
    "manufacturing_date": "string or null — copy exactly as written",
    "expiry_date": "string or null — copy exactly as written",
    "quantity_affected": "string or null — include units and packaging context",
    "complaint_type": "string or null (one of: Product Defect, Foreign Matter Contamination, Packaging Issue, Labeling Issue, Microbiological Contamination, Other)",
    "complaint_date": "string or null — date the complaint was reported",
    "description": "string or null — normalized complaint narrative in 1-3 sentences"
  }},
  "missing_fields": ["list of field names that are genuinely NOT present in the complaint text"],
  "confidence": {{
    "field_name": 0.0
  }}
}}

RULES:
- missing_fields should list field names (e.g. "expiry_date", "manufacturing_date") that are absent from the complaint
- confidence values should be between 0.0 (very uncertain) and 1.0 (clearly stated)
- Do NOT include a field in missing_fields if you set it to null due to it not being mentioned — include it ONLY if it is a required traceability field that is absent
- Required traceability fields: batch_lot_number, product_name, complaint_type
- description should summarize the core complaint in plain language"""


# ─────────────────────────────────────────────
# Risk assessment prompt
# ─────────────────────────────────────────────

RISK_ASSESSMENT_PROMPT_TEMPLATE = """Perform an initial pharmaceutical complaint risk assessment based on the following structured complaint data.

COMPLAINT DATA:
{complaint_json}

Return ONLY this JSON structure with no additional text:
{{
  "category": "string (e.g. Product Defect, Foreign Matter Contamination, Packaging Issue, Labeling Issue, Microbiological Contamination, Other)",
  "severity": "Minor|Major|Critical",
  "priority": "Low|Medium|High|Critical",
  "rationale": "string — 2-4 sentence evidence-based explanation referencing specific complaint details",
  "suggested_next_action": "string — specific QA/investigation recommendation"
}}

SEVERITY GUIDE:
- Critical: immediate patient/consumer safety risk, confirmed contamination, potential fatality/hospitalization, regulatory breach
- Major: significant quality deviation, potential recall, widespread batch impact, multiple units affected, sterility concern
- Minor: cosmetic defect isolated to few units, minor packaging issue, no safety risk identified

PRIORITY GUIDE:
- Critical: immediate action required within 24 hours
- High: urgent investigation required within 72 hours
- Medium: standard investigation within 7 days
- Low: routine investigation within 30 days

IMPORTANT: This is an INITIAL AI assessment to assist the QA reviewer. It is NOT a final regulatory or QA determination."""


# ─────────────────────────────────────────────
# Follow-up / correction prompt
# ─────────────────────────────────────────────

FOLLOWUP_PROMPT_TEMPLATE = """A pharmaceutical complaint intake operator wants to correct or update information in an existing complaint record.

CURRENT COMPLAINT STATE:
{current_complaint_json}

USER MESSAGE:
"{user_message}"

Determine what fields the user wants to update and extract the new values.

Return ONLY this JSON structure with no additional text:
{{
  "field_updates": {{
    "field_name": "new_value"
  }},
  "is_material_change": true,
  "clarification_needed": null
}}

RULES:
- field_updates must use ONLY these field names: complaint_source, customer_name, product_name, strength_grade, batch_lot_number, manufacturing_date, expiry_date, quantity_affected, complaint_type, complaint_date, description
- Only include fields that the user EXPLICITLY mentioned in their message
- is_material_change is true if any of these fields changed: batch_lot_number, product_name, complaint_type, strength_grade, quantity_affected, description
- If the user message is ambiguous (no clear field update), set field_updates to {{}} and set clarification_needed to a focused single question
- User corrections are AUTHORITATIVE — accept them without questioning
- Do NOT update fields the user did not mention"""


# ─────────────────────────────────────────────
# Copilot response generation prompt
# ─────────────────────────────────────────────

COPILOT_RESPONSE_PROMPT_TEMPLATE = """Generate a brief, professional response for a pharmaceutical complaint intake operator.

CONTEXT: {context}
COMPLAINT SUMMARY: {complaint_summary}
MISSING FIELDS: {missing_fields}
RISK: {risk_summary}
ACTION: {action}

Write a 2-4 sentence response in plain professional language. 
- Confirm what was extracted or updated
- Mention any important missing fields
- State the AI risk recommendation if available
- Tell the operator what to do next
Do NOT repeat the full complaint text. Do NOT use markdown formatting."""
