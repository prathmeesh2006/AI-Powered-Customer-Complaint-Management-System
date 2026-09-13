import React from 'react';
import ComplaintForm from './ComplaintForm';
import CopilotPanel from './CopilotPanel';

/**
 * Top-level workspace layout — two-column desktop, stacked on mobile.
 * Left: Complaint form (55-60%)
 * Right: AI Copilot (40-45%)
 */
export default function ComplaintWorkspace() {
  return (
    <div className="workspace">
      <div className="workspace-left">
        <ComplaintForm />
      </div>
      <div className="workspace-right">
        <CopilotPanel />
      </div>
    </div>
  );
}
