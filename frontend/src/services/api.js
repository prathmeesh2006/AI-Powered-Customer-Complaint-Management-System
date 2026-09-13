/**
 * API service layer — all communication with FastAPI backend.
 * Uses axios with a base URL proxy configured in vite.config.js.
 */
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 90000, // 90s for LLM calls
});

// Error normalizer
function normalizeError(err) {
  if (err.response?.data?.detail) {
    return new Error(err.response.data.detail);
  }
  if (err.response?.data?.message) {
    return new Error(err.response.data.message);
  }
  if (err.message) {
    return new Error(err.message);
  }
  return new Error('An unexpected error occurred');
}

/**
 * Analyze pasted complaint text.
 */
export async function analyzeText(text) {
  try {
    const resp = await api.post('/complaints/analyze-text', { text });
    return resp.data;
  } catch (err) {
    throw normalizeError(err);
  }
}

/**
 * Upload and analyze a complaint document (PDF or text).
 */
export async function analyzeFile(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await api.post('/complaints/analyze-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return resp.data;
  } catch (err) {
    throw normalizeError(err);
  }
}

/**
 * Send a conversational correction/follow-up message.
 */
export async function sendFollowUp(message, currentComplaint, currentRisk) {
  try {
    const resp = await api.post('/complaints/follow-up', {
      message,
      current_complaint: currentComplaint,
      current_risk: currentRisk,
    });
    return resp.data;
  } catch (err) {
    throw normalizeError(err);
  }
}

/**
 * Commit the reviewed complaint to the QMS Ledger.
 */
export async function commitComplaint(payload) {
  try {
    const resp = await api.post('/complaints/new/commit', payload);
    return resp.data;
  } catch (err) {
    throw normalizeError(err);
  }
}

/**
 * Get a committed complaint by ID.
 */
export async function getComplaint(id) {
  try {
    const resp = await api.get(`/complaints/${id}`);
    return resp.data;
  } catch (err) {
    throw normalizeError(err);
  }
}

/**
 * List recent complaints.
 */
export async function listComplaints(limit = 20) {
  try {
    const resp = await api.get('/complaints', { params: { limit } });
    return resp.data;
  } catch (err) {
    throw normalizeError(err);
  }
}

/**
 * Health check.
 */
export async function healthCheck() {
  try {
    const resp = await api.get('/health');
    return resp.data;
  } catch (err) {
    throw normalizeError(err);
  }
}
