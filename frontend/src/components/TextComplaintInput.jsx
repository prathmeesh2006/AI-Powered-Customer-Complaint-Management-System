import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { analyzeComplaintText } from '../features/complaint/complaintSlice';

const SAMPLE_COMPLAINTS = [
  {
    label: 'Example 1: Discolored capsules',
    text: `From: ABC Pharmacy
Date: September 10, 2026
Subject: Customer Complaint — Discolored Capsules

Dear Quality Team,

We received a complaint from one of our customers regarding Amoxicillin Capsules 500 mg from batch AMX240602. The customer reported that 12 capsules appeared discolored (yellowish-brown) compared to the expected white color. The affected pack was purchased on September 8, 2026. The expiry date on the packaging shows June 2027.

Please investigate and advise on appropriate action.

Regards,
ABC Pharmacy`,
  },
  {
    label: 'Example 2: Foreign matter contamination',
    text: `Customer Complaint Report

Product: Metformin Tablets 500mg
Batch Number: MET240901
Complaint Date: September 12, 2026
Customer: City Hospital Pharmacy
Quantity Affected: 3 tablets

The customer found small black particles embedded in 3 tablets from the above batch. This is potentially a foreign matter contamination issue. The product was dispensed from our hospital dispensary. Manufacturing date: July 2024. Expiry: July 2026.`,
  },
  {
    label: 'Example 3: Incomplete complaint (missing info)',
    text: `Hi,

A patient came to our counter and complained about some tablets that weren't working. They said the medicine tasted different than usual and seemed to dissolve faster than expected. We're not sure which batch it was from — they didn't bring the packaging. The patient took Atorvastatin but we don't know the strength.

Please advise.`,
  },
];

export default function TextComplaintInput() {
  const dispatch = useDispatch();
  const [text, setText] = useState('');

  function handleAnalyze() {
    if (text.trim().length >= 10) {
      dispatch(analyzeComplaintText(text.trim()));
    }
  }

  function handleKeyDown(e) {
    if (e.ctrlKey && e.key === 'Enter') handleAnalyze();
  }

  function loadSample(sample) {
    setText(sample.text);
  }

  return (
    <div className="text-input-area">
      <div className="flex items-center gap-2" style={{ marginBottom: '6px' }}>
        <span className="text-xs text-muted font-medium">Sample complaints:</span>
        {SAMPLE_COMPLAINTS.map((s, i) => (
          <button
            key={i}
            className="btn btn-sm btn-secondary"
            onClick={() => loadSample(s)}
            type="button"
            style={{ fontSize: '11px', height: '24px', padding: '0 8px' }}
            title={s.text.slice(0, 80)}
          >
            Ex {i + 1}
          </button>
        ))}
      </div>

      <textarea
        id="complaint-text-input"
        className="text-complaint-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Paste complaint email or text here…&#10;&#10;Example: 'ABC Pharmacy reported discolored capsules in Amoxicillin 500mg, batch AMX240602. 12 capsules affected.'"
        aria-label="Complaint text input"
      />

      <div className="flex items-center" style={{ justifyContent: 'space-between' }}>
        <span className="text-xs text-muted">
          Ctrl+Enter to analyze
        </span>
        <button
          className="btn btn-primary text-analyze-btn"
          onClick={handleAnalyze}
          disabled={text.trim().length < 10}
          type="button"
        >
          ✦ Analyze Complaint
        </button>
      </div>
    </div>
  );
}
