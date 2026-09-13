import React from 'react';

const FIELD_LABELS = {
  complaintSource: 'Complaint Source',
  customerName: 'Customer Name',
  productName: 'Product Name',
  strengthGrade: 'Strength/Grade',
  batchLotNumber: 'Batch/Lot Number',
  manufacturingDate: 'Manufacturing Date',
  expiryDate: 'Expiry Date',
  quantityAffected: 'Affected Quantity',
  complaintType: 'Complaint Type',
  complaintDate: 'Complaint Date',
  description: 'Description',
};

const MISSING_FIELD_LABELS = {
  batch_lot_number: 'Batch/Lot Number',
  product_name: 'Product Name',
  complaint_type: 'Complaint Type',
  complaint_source: 'Complaint Source',
  description: 'Description',
};

export default function CommitDialog({ fields, risk, missingFields, onConfirm, onCancel }) {
  const criticalMissing = (missingFields || []).filter(
    f => ['batch_lot_number', 'product_name', 'complaint_type'].includes(f)
  );

  return (
    <div className="modal-overlay">
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="commit-dialog-title">
        <div className="modal-header">
          <h2 className="modal-title" id="commit-dialog-title">Commit to QMS Ledger</h2>
          <button className="modal-close" onClick={onCancel} aria-label="Close dialog" type="button">✕</button>
        </div>

        <div className="modal-body">
          <p className="text-sm text-secondary" style={{ marginBottom: '14px' }}>
            Review the complaint record before committing. This action persists the complaint to the database.
          </p>

          {criticalMissing.length > 0 && (
            <div className="completeness-banner error" style={{ marginBottom: '14px' }}>
              <span className="completeness-icon">⚠</span>
              <div className="completeness-text">
                <div className="completeness-title">Required fields are missing</div>
                <div className="completeness-fields">
                  {criticalMissing.map(f => MISSING_FIELD_LABELS[f] || f).join(', ')}
                </div>
                <div className="completeness-fields" style={{ marginTop: '4px', opacity: 0.9 }}>
                  You may still commit, but the record will be flagged for follow-up.
                </div>
              </div>
            </div>
          )}

          <div className="commit-summary">
            {Object.entries(FIELD_LABELS).map(([key, label]) => {
              const val = fields[key];
              return (
                <div className="commit-summary-row" key={key}>
                  <span className="commit-summary-label">{label}</span>
                  <span className="commit-summary-value">
                    {val || <span style={{ color: 'var(--color-text-muted)' }}>Not provided</span>}
                  </span>
                </div>
              );
            })}
          </div>

          {risk && risk.severity && (
            <div style={{ marginTop: '4px' }}>
              <p className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                AI Risk Assessment
              </p>
              <div className="commit-summary">
                <div className="commit-summary-row">
                  <span className="commit-summary-label">Severity</span>
                  <span className={`risk-badge ${risk.severity}`} style={{ fontSize: '12px' }}>{risk.severity}</span>
                </div>
                <div className="commit-summary-row">
                  <span className="commit-summary-label">Priority</span>
                  <span className={`risk-badge ${risk.priority}`} style={{ fontSize: '12px' }}>{risk.priority}</span>
                </div>
                {risk.suggestedNextAction && (
                  <div className="commit-summary-row" style={{ flexDirection: 'column', gap: '4px' }}>
                    <span className="commit-summary-label">Suggested Action</span>
                    <span className="commit-summary-value">{risk.suggestedNextAction}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          <p className="text-xs text-muted" style={{ marginTop: '12px' }}>
            ℹ This record will be permanently saved. The AI risk assessment is an initial recommendation — final QA review is required.
          </p>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onCancel} type="button">Cancel</button>
          <button className="btn btn-commit" onClick={onConfirm} type="button">
            ✓ Confirm Commit
          </button>
        </div>
      </div>
    </div>
  );
}
