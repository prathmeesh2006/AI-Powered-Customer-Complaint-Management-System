import React from 'react';

export default function RiskAssessmentCard({ risk }) {
  if (!risk || !risk.severity) return null;

  const { category, severity, priority, rationale, suggestedNextAction } = risk;

  return (
    <div className="risk-card">
      <div className="risk-card-header">
        <span style={{ fontSize: '14px' }}>🛡</span>
        <span className="risk-card-title">Initial AI Risk Assessment</span>
        <span className="risk-label">AI Suggested</span>
      </div>

      <div className="risk-card-body">
        <div className="risk-grid">
          <div className="risk-item">
            <span className="risk-item-label">Category</span>
            <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
              {category || '—'}
            </span>
          </div>
          <div className="risk-item">
            <span className="risk-item-label">Severity</span>
            <span className={`risk-badge ${severity || ''}`}>{severity || '—'}</span>
          </div>
          <div className="risk-item">
            <span className="risk-item-label">Priority</span>
            <span className={`risk-badge ${priority || ''}`}>{priority || '—'}</span>
          </div>
        </div>

        {rationale && (
          <div className="risk-rationale">
            <div className="risk-item-label" style={{ marginBottom: '4px' }}>Risk Rationale</div>
            {rationale}
          </div>
        )}

        {suggestedNextAction && (
          <div className="risk-action">
            <div className="risk-action-label">Suggested Next Action</div>
            {suggestedNextAction}
          </div>
        )}

        <div className="risk-disclaimer">
          <span>ℹ</span>
          AI-generated recommendation. Final QA review required before regulatory disposition.
        </div>
      </div>
    </div>
  );
}
