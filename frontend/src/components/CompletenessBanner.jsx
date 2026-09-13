import React from 'react';

const FIELD_LABELS = {
  batch_lot_number: 'Batch/Lot Number',
  product_name: 'Product Name',
  complaint_type: 'Complaint Type',
  complaint_source: 'Complaint Source',
  customer_name: 'Customer Name',
  strength_grade: 'Strength/Grade',
  manufacturing_date: 'Manufacturing Date',
  expiry_date: 'Expiry Date',
  quantity_affected: 'Affected Quantity',
  complaint_date: 'Complaint Date',
  description: 'Description',
};

const REQUIRED_FIELDS = new Set(['batch_lot_number', 'product_name', 'complaint_type', 'description']);

export default function CompletenessBanner({ missingFields = [] }) {
  if (missingFields.length === 0) {
    return (
      <div className="completeness-banner ok">
        <span className="completeness-icon">✓</span>
        <div className="completeness-text">
          <div className="completeness-title">All key fields extracted</div>
        </div>
      </div>
    );
  }

  const required = missingFields.filter(f => REQUIRED_FIELDS.has(f));
  const preferred = missingFields.filter(f => !REQUIRED_FIELDS.has(f));
  const severity = required.length > 0 ? 'error' : 'warn';

  const title = required.length > 0
    ? `${required.length} required field${required.length > 1 ? 's' : ''} need attention`
    : `${missingFields.length} field${missingFields.length > 1 ? 's' : ''} not confirmed`;

  const icon = required.length > 0 ? '⚠' : '○';

  return (
    <div className={`completeness-banner ${severity}`}>
      <span className="completeness-icon">{icon}</span>
      <div className="completeness-text">
        <div className="completeness-title">{title}</div>
        {required.length > 0 && (
          <div className="completeness-fields">
            Required: {required.map(f => FIELD_LABELS[f] || f).join(', ')}
          </div>
        )}
        {preferred.length > 0 && (
          <div className="completeness-fields" style={{ marginTop: '2px', opacity: 0.8 }}>
            Preferred: {preferred.map(f => FIELD_LABELS[f] || f).join(', ')}
          </div>
        )}
      </div>
    </div>
  );
}
