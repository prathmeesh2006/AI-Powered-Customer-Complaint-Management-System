/**
 * Complaint Redux slice — canonical complaint draft state.
 *
 * Architecture (correction #4 & #5):
 * - Manual edits update Redux locally with no API call per keystroke
 * - AI analysis results flow into Redux draft
 * - User corrections take priority and are tracked in fieldMeta
 * - Draft lives in Redux until explicit commit
 * - Database record is only created on commit
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { analyzeText, analyzeFile, sendFollowUp, commitComplaint } from '../../services/api';

// Field metadata tracks how each field got its value
const createEmptyFieldMeta = () => ({
  source: 'empty',     // 'empty' | 'ai' | 'uncertain' | 'corrected' | 'locked'
  confidence: null,
});

const COMPLAINT_FIELDS = [
  'complaintSource', 'customerName', 'productName', 'strengthGrade',
  'batchLotNumber', 'manufacturingDate', 'expiryDate', 'quantityAffected',
  'complaintType', 'complaintDate', 'description',
];

const FIELD_MAP = {
  // API (snake_case) → Redux (camelCase)
  complaint_source: 'complaintSource',
  customer_name: 'customerName',
  product_name: 'productName',
  strength_grade: 'strengthGrade',
  batch_lot_number: 'batchLotNumber',
  manufacturing_date: 'manufacturingDate',
  expiry_date: 'expiryDate',
  quantity_affected: 'quantityAffected',
  complaint_type: 'complaintType',
  complaint_date: 'complaintDate',
  description: 'description',
};

// Reverse map for API submission
const FIELD_MAP_REVERSE = Object.fromEntries(
  Object.entries(FIELD_MAP).map(([k, v]) => [v, k])
);

function emptyFields() {
  return Object.fromEntries(COMPLAINT_FIELDS.map(f => [f, '']));
}

function emptyFieldMeta() {
  return Object.fromEntries(COMPLAINT_FIELDS.map(f => [f, createEmptyFieldMeta()]));
}

/**
 * Convert snake_case API complaint to camelCase Redux fields.
 * Marks each field with its AI source metadata.
 */
function mapApiComplaintToRedux(apiComplaint, confidence = {}) {
  const fields = {};
  const meta = emptyFieldMeta();

  for (const [apiKey, reduxKey] of Object.entries(FIELD_MAP)) {
    const val = apiComplaint[apiKey];
    fields[reduxKey] = val || '';
    if (val) {
      const conf = confidence[apiKey];
      meta[reduxKey] = {
        source: (conf !== undefined && conf < 0.7) ? 'uncertain' : 'ai',
        confidence: conf ?? null,
      };
    }
  }

  return { fields, meta };
}

/**
 * Convert camelCase Redux fields back to snake_case for API submission.
 */
export function mapReduxFieldsToApi(fields) {
  const result = {};
  for (const [reduxKey, apiKey] of Object.entries(FIELD_MAP_REVERSE)) {
    const val = fields[reduxKey];
    result[apiKey] = val || null;
  }
  return result;
}

const initialState = {
  // Draft complaint fields
  fields: emptyFields(),
  fieldMeta: emptyFieldMeta(),

  // AI risk assessment
  risk: {
    category: null,
    severity: null,
    priority: null,
    rationale: null,
    suggestedNextAction: null,
  },

  // Metadata
  missingFields: [],       // API field names (snake_case)
  confidence: {},
  sourceMetadata: {},      // filename, mime_type if document upload

  // Workflow status
  // 'idle' | 'processing' | 'review' | 'committed' | 'error'
  status: 'idle',
  committedId: null,
  committedAt: null,
  error: null,
};

// ─────────────────────────────────────────────
// Async thunks
// ─────────────────────────────────────────────

export const analyzeComplaintText = createAsyncThunk(
  'complaint/analyzeText',
  async (text, { rejectWithValue }) => {
    try {
      return await analyzeText(text);
    } catch (err) {
      return rejectWithValue(err.message || 'AI analysis failed');
    }
  }
);

export const analyzeComplaintFile = createAsyncThunk(
  'complaint/analyzeFile',
  async (file, { rejectWithValue }) => {
    try {
      return await analyzeFile(file);
    } catch (err) {
      return rejectWithValue(err.message || 'File analysis failed');
    }
  }
);

export const sendCopilotFollowUp = createAsyncThunk(
  'complaint/followUp',
  async ({ message, currentComplaint, currentRisk }, { rejectWithValue }) => {
    try {
      return await sendFollowUp(message, currentComplaint, currentRisk);
    } catch (err) {
      return rejectWithValue(err.message || 'Follow-up failed');
    }
  }
);

export const commitToQmsLedger = createAsyncThunk(
  'complaint/commit',
  async ({ fields, risk, missingFields, confidence, sourceFilename }, { rejectWithValue }) => {
    try {
      const apiFields = mapReduxFieldsToApi(fields);
      const apiRisk = risk ? {
        category: risk.category,
        severity: risk.severity,
        priority: risk.priority,
        rationale: risk.rationale,
        suggested_next_action: risk.suggestedNextAction,
      } : null;

      return await commitComplaint({
        complaint: apiFields,
        risk: apiRisk,
        missing_fields: missingFields,
        confidence,
        source_filename: sourceFilename,
      });
    } catch (err) {
      return rejectWithValue(err.message || 'Commit failed');
    }
  }
);

// ─────────────────────────────────────────────
// Slice
// ─────────────────────────────────────────────

const complaintSlice = createSlice({
  name: 'complaint',
  initialState,
  reducers: {
    // Manual field edit — updates Redux locally, no API call (correction #4)
    setField(state, action) {
      const { fieldName, value } = action.payload;
      if (fieldName in state.fields) {
        state.fields[fieldName] = value;
        // Mark as user-corrected
        state.fieldMeta[fieldName] = { source: 'corrected', confidence: 1.0 };
      }
    },

    // Reset entire workspace
    resetComplaint() {
      return { ...initialState };
    },

    // Mark status
    setStatus(state, action) {
      state.status = action.payload;
    },

    clearError(state) {
      state.error = null;
    },
  },

  extraReducers: (builder) => {
    // ── analyzeComplaintText ──
    builder
      .addCase(analyzeComplaintText.pending, (state) => {
        state.status = 'processing';
        state.error = null;
      })
      .addCase(analyzeComplaintText.fulfilled, (state, action) => {
        const { complaint, risk, missing_fields, confidence, source_filename } = action.payload;
        const { fields, meta } = mapApiComplaintToRedux(complaint, confidence);
        state.fields = fields;
        state.fieldMeta = meta;
        state.risk = {
          category: risk?.category || null,
          severity: risk?.severity || null,
          priority: risk?.priority || null,
          rationale: risk?.rationale || null,
          suggestedNextAction: risk?.suggested_next_action || null,
        };
        state.missingFields = missing_fields || [];
        state.confidence = confidence || {};
        state.sourceMetadata = source_filename ? { filename: source_filename } : {};
        state.status = 'review';
        state.error = null;
      })
      .addCase(analyzeComplaintText.rejected, (state, action) => {
        // Preserve existing form data on error (correction #8 spirit)
        state.status = state.status === 'processing' ? 'idle' : state.status;
        state.error = action.payload || 'Analysis failed';
      });

    // ── analyzeComplaintFile ──
    builder
      .addCase(analyzeComplaintFile.pending, (state) => {
        state.status = 'processing';
        state.error = null;
      })
      .addCase(analyzeComplaintFile.fulfilled, (state, action) => {
        const { complaint, risk, missing_fields, confidence, source_filename } = action.payload;
        const { fields, meta } = mapApiComplaintToRedux(complaint, confidence);
        state.fields = fields;
        state.fieldMeta = meta;
        state.risk = {
          category: risk?.category || null,
          severity: risk?.severity || null,
          priority: risk?.priority || null,
          rationale: risk?.rationale || null,
          suggestedNextAction: risk?.suggested_next_action || null,
        };
        state.missingFields = missing_fields || [];
        state.confidence = confidence || {};
        state.sourceMetadata = { filename: source_filename };
        state.status = 'review';
        state.error = null;
      })
      .addCase(analyzeComplaintFile.rejected, (state, action) => {
        state.status = state.status === 'processing' ? 'idle' : state.status;
        state.error = action.payload || 'File analysis failed';
      });

    // ── sendCopilotFollowUp ──
    builder
      .addCase(sendCopilotFollowUp.fulfilled, (state, action) => {
        const { complaint, risk, missing_fields } = action.payload;
        if (!complaint) return;

        // Apply only the returned fields — preserve unrelated fields (correction #7)
        const { fields, meta } = mapApiComplaintToRedux(complaint, {});
        
        // Merge: only update fields that API returned with non-empty values
        for (const [reduxKey] of Object.entries(state.fields)) {
          const apiKey = FIELD_MAP_REVERSE[reduxKey];
          if (apiKey && complaint[apiKey] !== undefined) {
            state.fields[reduxKey] = fields[reduxKey];
            if (fields[reduxKey]) {
              state.fieldMeta[reduxKey] = { source: 'corrected', confidence: 1.0 };
            }
          }
        }

        // Update risk if reassessment happened
        if (risk && risk.severity) {
          state.risk = {
            category: risk.category || null,
            severity: risk.severity || null,
            priority: risk.priority || null,
            rationale: risk.rationale || null,
            suggestedNextAction: risk.suggested_next_action || null,
          };
        }

        if (missing_fields) state.missingFields = missing_fields;
        state.status = 'review';
      })
      .addCase(sendCopilotFollowUp.rejected, (state, action) => {
        // Preserve complaint state on follow-up error
        state.error = action.payload || 'Follow-up failed';
      });

    // ── commitToQmsLedger ──
    builder
      .addCase(commitToQmsLedger.pending, (state) => {
        state.error = null;
      })
      .addCase(commitToQmsLedger.fulfilled, (state, action) => {
        state.status = 'committed';
        state.committedId = action.payload.complaint_id;
        state.committedAt = action.payload.committed_at;
        // Lock all fields after commit
        for (const key of Object.keys(state.fieldMeta)) {
          state.fieldMeta[key] = { source: 'locked', confidence: state.fieldMeta[key]?.confidence };
        }
      })
      .addCase(commitToQmsLedger.rejected, (state, action) => {
        // Never claim success — error is surfaced to user (correction #6 spirit)
        state.error = action.payload || 'Database commit failed';
      });
  },
});

export const { setField, resetComplaint, setStatus, clearError } = complaintSlice.actions;

// Selectors
export const selectComplaintFields = (state) => state.complaint.fields;
export const selectFieldMeta = (state) => state.complaint.fieldMeta;
export const selectRisk = (state) => state.complaint.risk;
export const selectMissingFields = (state) => state.complaint.missingFields;
export const selectComplaintStatus = (state) => state.complaint.status;
export const selectCommittedId = (state) => state.complaint.committedId;
export const selectComplaintError = (state) => state.complaint.error;

export default complaintSlice.reducer;
