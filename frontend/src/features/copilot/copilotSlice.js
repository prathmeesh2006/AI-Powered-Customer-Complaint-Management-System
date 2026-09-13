/**
 * Copilot Redux slice — manages AI conversation, processing state, and progress stages.
 */
import { createSlice } from '@reduxjs/toolkit';
import {
  analyzeComplaintText,
  analyzeComplaintFile,
  sendCopilotFollowUp,
  commitToQmsLedger,
} from '../complaint/complaintSlice';

// Extraction workflow stages shown in the UI
export const PROCESSING_STAGES = [
  { id: 'uploading', label: 'Uploading' },
  { id: 'reading', label: 'Reading complaint' },
  { id: 'extracting', label: 'Extracting details' },
  { id: 'validating', label: 'Validating fields' },
  { id: 'assessing', label: 'Assessing risk' },
  { id: 'preparing', label: 'Preparing QMS record' },
  { id: 'ready', label: 'Ready for review' },
];

const initialState = {
  messages: [],          // [{id, role, content, timestamp}]
  isProcessing: false,
  currentStage: null,    // stage id from PROCESSING_STAGES
  stageIndex: -1,
  error: null,
  inputMode: 'upload',   // 'upload' | 'text'
};

let messageIdCounter = 0;
function newMessage(role, content) {
  return {
    id: `msg-${++messageIdCounter}-${Date.now()}`,
    role,
    content,
    timestamp: new Date().toISOString(),
  };
}

const copilotSlice = createSlice({
  name: 'copilot',
  initialState,
  reducers: {
    setInputMode(state, action) {
      state.inputMode = action.payload;
    },

    addMessage(state, action) {
      state.messages.push(newMessage(action.payload.role, action.payload.content));
    },

    setStage(state, action) {
      const stageId = action.payload;
      const idx = PROCESSING_STAGES.findIndex(s => s.id === stageId);
      state.currentStage = stageId;
      state.stageIndex = idx;
    },

    clearError(state) {
      state.error = null;
    },

    resetCopilot() {
      return { ...initialState };
    },
  },

  extraReducers: (builder) => {
    // ── Text analysis ──
    builder
      .addCase(analyzeComplaintText.pending, (state, action) => {
        state.isProcessing = true;
        state.error = null;
        state.currentStage = 'reading';
        state.stageIndex = 1;
        state.messages.push(
          newMessage('user', `Complaint text submitted for analysis.`)
        );
      })
      .addCase(analyzeComplaintText.fulfilled, (state, action) => {
        state.isProcessing = false;
        state.currentStage = 'ready';
        state.stageIndex = PROCESSING_STAGES.length - 1;
        const msg = action.payload.copilot_message;
        if (msg) {
          state.messages.push(newMessage('assistant', msg));
        }
        state.error = null;
      })
      .addCase(analyzeComplaintText.rejected, (state, action) => {
        state.isProcessing = false;
        state.currentStage = null;
        state.error = action.payload || 'Analysis failed';
        state.messages.push(
          newMessage('assistant',
            "I couldn't complete the AI analysis. Your current form data is preserved. " +
            "Please check your internet connection and retry, or paste the complaint text again."
          )
        );
      });

    // ── File analysis ──
    builder
      .addCase(analyzeComplaintFile.pending, (state) => {
        state.isProcessing = true;
        state.error = null;
        state.currentStage = 'uploading';
        state.stageIndex = 0;
      })
      .addCase(analyzeComplaintFile.fulfilled, (state, action) => {
        state.isProcessing = false;
        state.currentStage = 'ready';
        state.stageIndex = PROCESSING_STAGES.length - 1;
        const msg = action.payload.copilot_message;
        const filename = action.payload.source_filename;
        if (filename) {
          state.messages.push(newMessage('user', `Document uploaded: ${filename}`));
        }
        if (msg) {
          state.messages.push(newMessage('assistant', msg));
        }
        state.error = null;
      })
      .addCase(analyzeComplaintFile.rejected, (state, action) => {
        state.isProcessing = false;
        state.currentStage = null;
        state.error = action.payload || 'File analysis failed';
        state.messages.push(
          newMessage('assistant',
            "The document could not be read in the demo parser. " +
            "Try another file or paste the complaint text directly."
          )
        );
      });

    // ── Follow-up ──
    builder
      .addCase(sendCopilotFollowUp.pending, (state) => {
        state.isProcessing = true;
        state.error = null;
      })
      .addCase(sendCopilotFollowUp.fulfilled, (state, action) => {
        state.isProcessing = false;
        state.error = null;
        const msg = action.payload.copilot_message;
        if (msg) {
          state.messages.push(newMessage('assistant', msg));
        }
      })
      .addCase(sendCopilotFollowUp.rejected, (state, action) => {
        state.isProcessing = false;
        state.error = action.payload || 'Follow-up failed';
        state.messages.push(
          newMessage('assistant',
            "I couldn't process your correction. Please try again."
          )
        );
      });

    // ── Commit ──
    builder
      .addCase(commitToQmsLedger.fulfilled, (state, action) => {
        state.messages.push(
          newMessage('assistant',
            `✓ Complaint committed to QMS Ledger successfully. ID: ${action.payload.complaint_id}`
          )
        );
      })
      .addCase(commitToQmsLedger.rejected, (state, action) => {
        state.messages.push(
          newMessage('assistant',
            "Database commit failed. Your complaint data is preserved — please retry."
          )
        );
      });
  },
});

export const { setInputMode, addMessage, setStage, clearError, resetCopilot } = copilotSlice.actions;

export const selectMessages = (state) => state.copilot.messages;
export const selectIsProcessing = (state) => state.copilot.isProcessing;
export const selectCurrentStage = (state) => state.copilot.currentStage;
export const selectStageIndex = (state) => state.copilot.stageIndex;
export const selectCopilotError = (state) => state.copilot.error;
export const selectInputMode = (state) => state.copilot.inputMode;

export default copilotSlice.reducer;
