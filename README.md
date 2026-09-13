# AIVOA — AI-Powered Customer Complaint Management System

> **AIVOA AI Product Engineer Internship — Round 1**  
> Pharmaceutical QMS Complaint Intake with LangGraph + Groq + React + Redux

---

## Overview

AIVOA is an AI-assisted Customer Complaint Intake and Risk Assessment application for pharmaceutical manufacturing QMS workflows. It converts unstructured complaint text or uploaded documents into structured QMS complaint records through a LangGraph AI pipeline, providing initial risk assessment, supporting conversational corrections, and persisting finalized complaints to a relational database.

**Core workflow:**
```
User Input (text/PDF)
  → FastAPI
  → LangGraph workflow
  → Groq LLM (gemma2-9b-it)
  → Structured extraction + validation
  → AI risk assessment
  → Redux state (form auto-populates)
  → Human review & conversational corrections
  → Explicit Commit to QMS Ledger
  → PostgreSQL/SQLite persistence
```

---

## Features

### Core (Implemented)
- ✅ **Text/Email intake** — paste complaint text and analyze with AI
- ✅ **PDF/document upload** — drag-and-drop or browse
- ✅ **LangGraph AI workflow** — real graph nodes, not mocked
- ✅ **Groq LLM integration** — gemma2-9b-it model
- ✅ **Structured extraction** — Pydantic-validated LLM output
- ✅ **Missing field detection** — never hallucinates missing data
- ✅ **Initial risk assessment** — severity, priority, rationale, suggested action
- ✅ **Form auto-population** — Redux draft updated from AI response
- ✅ **Conversational corrections** — natural language field updates
- ✅ **Targeted field updates** — only changed fields update, others preserved
- ✅ **Material change reassessment** — risk re-evaluated when key fields change
- ✅ **QMS Ledger commit** — explicit user action, real database write
- ✅ **Completeness checker** — flags missing required/preferred fields
- ✅ **Audit trail** — correction and assessment events recorded
- ✅ **Duplicate detection** — finds potentially matching complaints
- ✅ **Error handling** — graceful fallbacks for all failure modes

### Bonus
- ✅ Complaint completeness checker (P0)
- ✅ AI risk classification (P0)
- ✅ Duplicate complaint detection (P1)

---

## Architecture

```
┌─────────────────────────────────────────────┐
│            Browser (React + Redux)           │
│   complaintSlice  ←→  copilotSlice          │
└────────────────┬────────────────────────────┘
                 │ Fetch/Axios REST
┌────────────────▼────────────────────────────┐
│          FastAPI API Layer                   │
│  /analyze-text  /analyze-file  /follow-up   │
│  /new/commit    /complaints     /health      │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│     document_parser.py (file → text)        │
│              ↓                              │
│        LangGraph State Machine              │
│  ┌──────────────────────────────────────┐  │
│  │  complaint_graph:                    │  │
│  │  extract_complaint                   │  │
│  │    → validate_fields                 │  │
│  │    → assess_risk                     │  │
│  │    → build_copilot_response          │  │
│  │                                      │  │
│  │  followup_graph:                     │  │
│  │  understand_followup                 │  │
│  │    → merge_state                     │  │
│  │    → reassess_if_needed              │  │
│  │    → build_correction_response       │  │
│  └──────────────────────────────────────┘  │
│              ↓                              │
│    Groq LLM (gemma2-9b-it)                 │
│    Pydantic schema validation + retry       │
└────────────────┬────────────────────────────┘
                 │ SQLAlchemy
┌────────────────▼────────────────────────────┐
│   PostgreSQL / SQLite                       │
│  complaints  complaint_assessments          │
│  complaint_events  source_documents         │
└─────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + Vite |
| State | Redux Toolkit |
| HTTP | Axios |
| Font | Inter (Google Fonts) |
| Backend | Python + FastAPI |
| AI Orchestration | LangGraph |
| LLM | Groq — gemma2-9b-it |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL (recommended) / SQLite (dev) |
| PDF Parsing | pypdf |

---

## Folder Structure

```
AIVOA_Project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings from .env
│   │   ├── api/routes/
│   │   │   └── complaints.py    # All API endpoints
│   │   ├── ai/
│   │   │   ├── state.py         # ComplaintState TypedDict
│   │   │   ├── nodes.py         # LangGraph nodes (all AI logic)
│   │   │   ├── graph.py         # Graph assembly + compilation
│   │   │   ├── prompts.py       # LLM prompts
│   │   │   └── validators.py    # Pydantic LLM output validators
│   │   ├── models/
│   │   │   └── complaint.py     # SQLAlchemy ORM models
│   │   ├── schemas/
│   │   │   └── complaint.py     # Pydantic API schemas
│   │   ├── services/
│   │   │   ├── complaint_service.py  # Business logic
│   │   │   └── document_parser.py    # File → text conversion
│   │   └── db/
│   │       ├── session.py       # SQLAlchemy session factory
│   │       └── base.py          # Declarative base
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_complaint_workflow.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/store.js
│   │   ├── features/
│   │   │   ├── complaint/complaintSlice.js
│   │   │   └── copilot/copilotSlice.js
│   │   ├── components/
│   │   │   ├── ComplaintWorkspace.jsx
│   │   │   ├── ComplaintForm.jsx
│   │   │   ├── CopilotPanel.jsx
│   │   │   ├── RiskAssessmentCard.jsx
│   │   │   ├── FormField.jsx
│   │   │   ├── UploadDropzone.jsx
│   │   │   ├── TextComplaintInput.jsx
│   │   │   ├── ExtractionProgress.jsx
│   │   │   ├── CompletenessBanner.jsx
│   │   │   ├── CommitDialog.jsx
│   │   │   └── Toast.jsx
│   │   ├── services/api.js
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── sample_data/              # Synthetic pharmaceutical complaints
└── README.md
```

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (or use SQLite for local development)
- Groq API key (free at https://console.groq.com)

### 1. Clone / navigate to the project

```bash
cd c:\AIVOA_Project
```

### 2. Backend setup

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env
```

Edit `.env` and fill in:
```env
GROQ_API_KEY=your_actual_groq_api_key
GROQ_MODEL=gemma2-9b-it
DATABASE_URL=sqlite:///./aivoa_dev.db   # SQLite for dev
# OR for PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost:5432/aivoa_db
```

### 4. Database

The app auto-creates tables on startup (no Alembic required for dev).

For PostgreSQL, first create the database:
```sql
CREATE DATABASE aivoa_db;
```

### 5. Run the backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### 7. Open the app

Navigate to **http://localhost:5173**

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key | Required |
| `GROQ_MODEL` | Groq model to use | `gemma2-9b-it` |
| `GROQ_TIMEOUT` | LLM call timeout (seconds) | `60` |
| `DATABASE_URL` | SQLAlchemy database URL | SQLite dev DB |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173` |
| `MAX_UPLOAD_SIZE_MB` | Maximum file upload size | `10` |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/complaints/analyze-text` | Analyze complaint text |
| `POST` | `/api/complaints/analyze-file` | Upload and analyze document |
| `POST` | `/api/complaints/follow-up` | Conversational correction |
| `POST` | `/api/complaints/new/commit` | Commit to QMS Ledger |
| `GET` | `/api/complaints/{id}` | Get committed complaint |
| `GET` | `/api/complaints` | List recent complaints |
| `POST` | `/api/complaints/check-duplicates` | Find potential duplicates |

Interactive API docs: **http://localhost:8000/docs**

---

## LangGraph Architecture

### Nodes (in `app/ai/nodes.py`)

| Node | Responsibility |
|------|---------------|
| `extract_complaint` | Calls Groq LLM to extract structured fields. Pydantic validation + 1 retry. |
| `validate_fields` | Detects missing required/preferred fields without hallucinating values. |
| `assess_risk` | Calls Groq LLM for initial severity/priority/rationale. Pydantic validation + 1 retry. |
| `build_copilot_response` | Generates human-readable assistant message. |
| `understand_followup` | Parses correction message and identifies field changes via LLM. |
| `merge_state` | Applies user corrections with priority over AI extractions. |
| `reassess_if_needed` | Re-runs `assess_risk` only when material fields changed. |
| `build_correction_response` | Confirms what was updated in plain language. |

### Graphs

**complaint_graph**: `extract → validate → assess_risk → build_response`  
**followup_graph**: `understand_followup → merge_state → reassess_if_needed → build_correction_response`

---

## Example Complaint Workflow

### Demo 1: Text complaint
1. Click **"Paste Text"** tab
2. Click **"Ex 1"** to load the sample discoloration complaint
3. Click **"Analyze Complaint"**
4. Watch the form auto-populate with AI-extracted fields
5. Review the AI risk assessment (Major severity, High priority)

### Demo 2: Conversational correction
1. After analysis, type in the correction box: *"Sorry, the batch number is BMX240602 and quantity is 48 capsules"*
2. Press Enter or click Send
3. Watch only those two fields update — risk is reassessed automatically

### Demo 3: QMS commit
1. With fields populated, click **"Commit to QMS Ledger"**
2. Review the commit dialog
3. Click **"Confirm Commit"**
4. Record is persisted to the database with complaint ID

---

## Testing

Run tests without Groq API (validation, commit, health):

```bash
cd backend
pytest tests/test_complaint_workflow.py::test_health_check tests/test_complaint_workflow.py::test_qms_commit tests/test_complaint_workflow.py::test_short_text_rejected -v
```

Run all tests (requires valid `GROQ_API_KEY`):

```bash
cd backend
pytest tests/ -v
```

---

## Known Limitations

1. **PDF OCR**: Image-based PDFs are not supported (no production OCR). Text-based PDFs work well.
2. **LLM variability**: gemma2-9b-it output quality varies; the system retries once on parse failure.
3. **SQLite for dev**: Switch to PostgreSQL for production — SQLite has concurrency limitations.
4. **No authentication**: Demo scope — no user auth or role-based access control.
5. **AI assessments**: Initial recommendations only — not a substitute for QA review.

---

## Human-in-the-Loop Design

The system is designed so:
- The AI **extracts and suggests** — never decides
- Every form field shows its source (AI, user-corrected, uncertain, missing)
- The AI risk assessment is always labeled "Initial AI Assessment — QA review required"
- The QMS commit is always an **explicit user action** — never automatic
- The database record is only created after human review and explicit commit
- Conversational corrections are validated before being applied

---

## Screenshots

*Screenshots to be added after demo deployment.*

---

## License

This project was created for the AIVOA AI Product Engineer Internship evaluation (Round 1).
For evaluation purposes only — synthetic/demo data only.
