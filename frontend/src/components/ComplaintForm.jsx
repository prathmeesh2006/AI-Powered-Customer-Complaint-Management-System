import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  selectComplaintFields,
  selectComplaintStatus,
  selectMissingFields,
  selectRisk,
  setField,
  resetComplaint,
  commitToQmsLedger,
} from '../features/complaint/complaintSlice';
import { resetCopilot } from '../features/copilot/copilotSlice';
import FormSection from './FormSection';
import FormField from './FormField';
import CompletenessBanner from './CompletenessBanner';
import CommitDialog from './CommitDialog';

const SOURCE_OPTIONS = ['Pharmacy', 'Email', 'Customer', 'Distributor', 'Regulatory Authority', 'Other'];
const TYPE_OPTIONS = [
  'Product Defect', 'Foreign Matter Contamination', 'Packaging Issue',
  'Labeling Issue', 'Microbiological Contamination', 'Other',
];
const SEVERITY_OPTIONS = ['Minor', 'Major', 'Critical'];
const PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical'];

export default function ComplaintForm() {
  const dispatch = useDispatch();
  const fields = useSelector(selectComplaintFields);
  const status = useSelector(selectComplaintStatus);
  const missingFields = useSelector(selectMissingFields);
  const risk = useSelector(selectRisk);
  const [showCommitDialog, setShowCommitDialog] = useState(false);

  const isLocked = status === 'committed';
  const isProcessing = status === 'processing';

  // Local field change handler — updates Redux draft only, no API call
  function handleFieldChange(fieldName, value) {
    if (!isLocked && !isProcessing) {
      dispatch(setField({ fieldName, value }));
    }
  }

  function handleReset() {
    dispatch(resetComplaint());
    dispatch(resetCopilot());
  }

  function handleCommitClick() {
    setShowCommitDialog(true);
  }

  function handleCommitConfirm() {
    setShowCommitDialog(false);
    dispatch(commitToQmsLedger({
      fields,
      risk,
      missingFields,
      confidence: {},
      sourceFilename: null,
    }));
  }

  const committedBanner = isLocked && (
    <div className="committed-banner">
      <span className="committed-icon">✓</span>
      <div className="committed-text">
        <div className="committed-title">Complaint committed to QMS Ledger</div>
        <div className="committed-id">Record saved successfully</div>
      </div>
    </div>
  );

  return (
    <div className="panel" style={{ position: 'relative' }}>
      <div className="panel-header">
        <div>
          <div className="panel-title">Log Customer Complaint</div>
          <div className="panel-subtitle">Review and correct AI-extracted fields before committing</div>
        </div>
      </div>

      {committedBanner}

      <div className="panel-body">
        {(status === 'review' || status === 'committed') && (
          <CompletenessBanner missingFields={missingFields} />
        )}

        {/* Section 1: Origin & Customer Details */}
        <FormSection number="1" title="Origin & Customer Details">
          <div className="form-grid">
            <FormField
              id="complaint-source"
              label="Complaint Source"
              fieldName="complaintSource"
              required
              options={SOURCE_OPTIONS}
              value={fields.complaintSource}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
            <FormField
              id="customer-name"
              label="Customer Name"
              fieldName="customerName"
              placeholder="Organization or individual name"
              value={fields.customerName}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
          </div>
        </FormSection>

        {/* Section 2: Product & Batch Identification */}
        <FormSection number="2" title="Product & Batch Identification">
          <div className="form-grid">
            <FormField
              id="product-name"
              label="Product Name"
              fieldName="productName"
              required
              placeholder="e.g. Amoxicillin Capsules"
              value={fields.productName}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
            <FormField
              id="strength-grade"
              label="Strength / Grade"
              fieldName="strengthGrade"
              placeholder="e.g. 500 mg, Grade A"
              value={fields.strengthGrade}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
            <FormField
              id="batch-lot"
              label="Batch / Lot Number"
              fieldName="batchLotNumber"
              required
              placeholder="e.g. AMX240602"
              value={fields.batchLotNumber}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
            <FormField
              id="quantity-affected"
              label="Quantity Affected"
              fieldName="quantityAffected"
              placeholder="e.g. 12 capsules"
              value={fields.quantityAffected}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
            <FormField
              id="manufacturing-date"
              label="Manufacturing Date"
              fieldName="manufacturingDate"
              type="text"
              placeholder="e.g. Jan 2024"
              value={fields.manufacturingDate}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
            <FormField
              id="expiry-date"
              label="Expiry Date"
              fieldName="expiryDate"
              type="text"
              placeholder="e.g. Jun 2026"
              value={fields.expiryDate}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
          </div>
        </FormSection>

        {/* Section 3: Complaint Details */}
        <FormSection number="3" title="Complaint Details">
          <div className="form-grid">
            <FormField
              id="complaint-type"
              label="Complaint Type"
              fieldName="complaintType"
              required
              options={TYPE_OPTIONS}
              value={fields.complaintType}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
            <FormField
              id="complaint-date"
              label="Complaint Date"
              fieldName="complaintDate"
              type="text"
              placeholder="e.g. Sep 10, 2026"
              value={fields.complaintDate}
              onChange={handleFieldChange}
              disabled={isLocked}
            />
            <div className="form-grid-single">
              <FormField
                id="description"
                label="Detailed Complaint Description"
                fieldName="description"
                required
                rows={4}
                placeholder="Describe the complaint in detail..."
                value={fields.description}
                onChange={handleFieldChange}
                disabled={isLocked}
              />
            </div>
          </div>
        </FormSection>

        {/* Section 4: Initial Assessment & Priority */}
        <FormSection number="4" title="Initial Assessment & Priority">
          <div className="form-grid">
            <FormField
              id="severity"
              label="Initial Severity"
              fieldName="severity"
              options={SEVERITY_OPTIONS}
              value={risk?.severity || ''}
              onChange={(_, val) => {/* handled via risk state */}}
              disabled={isLocked}
            />
            <FormField
              id="priority"
              label="Priority"
              fieldName="priority"
              options={PRIORITY_OPTIONS}
              value={risk?.priority || ''}
              onChange={(_, val) => {}}
              disabled={isLocked}
            />
          </div>
          <p className="text-xs text-muted" style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>✦</span> Initial AI assessment — see risk panel for full rationale. Final QA review required.
          </p>
        </FormSection>
      </div>

      {/* Form Actions */}
      <div className="form-actions">
        <button
          className="btn btn-danger btn-sm"
          onClick={handleReset}
          disabled={isProcessing}
          type="button"
        >
          ↺ Reset Form
        </button>
        <div className="form-actions-right">
          {status === 'review' && (
            <button
              className="btn btn-commit"
              onClick={handleCommitClick}
              type="button"
            >
              ✓ Commit to QMS Ledger
            </button>
          )}
        </div>
      </div>

      {showCommitDialog && (
        <CommitDialog
          fields={fields}
          risk={risk}
          missingFields={missingFields}
          onConfirm={handleCommitConfirm}
          onCancel={() => setShowCommitDialog(false)}
        />
      )}
    </div>
  );
}
