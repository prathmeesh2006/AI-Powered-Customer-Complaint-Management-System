import React from 'react';
import { useSelector } from 'react-redux';
import { selectComplaintStatus, selectCommittedId } from '../features/complaint/complaintSlice';

const STATUS_LABELS = {
  idle: 'Draft',
  processing: 'AI Processing',
  review: 'Ready for Review',
  committed: 'Committed',
  error: 'Draft',
};

export default function Header() {
  const status = useSelector(selectComplaintStatus);
  const committedId = useSelector(selectCommittedId);
  const label = STATUS_LABELS[status] || 'Draft';

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="header-logo">AI</div>
        <div>
          <span className="header-title">AIVOA</span>
          <span className="header-subtitle">Complaint Management</span>
        </div>
      </div>

      <div className="header-right">
        {committedId && (
          <span className="text-xs text-muted font-medium" style={{ fontFamily: 'monospace' }}>
            ID: {committedId.slice(0, 8)}…
          </span>
        )}
        <span className={`status-chip ${status === 'processing' ? 'processing' : status === 'review' ? 'review' : status === 'committed' ? 'committed' : 'draft'}`}>
          <span className="status-chip-dot" />
          {label}
        </span>
      </div>
    </header>
  );
}
