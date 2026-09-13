import React from 'react';
import { useSelector } from 'react-redux';
import { selectFieldMeta } from '../features/complaint/complaintSlice';

/**
 * Individual form field with AI/uncertain/corrected/missing state indicators.
 * Manual edits dispatch setField to Redux — no API call per keystroke.
 */
export default function FormField({
  id,
  label,
  fieldName,
  required = false,
  type = 'text',
  options = null,   // for select fields
  disabled = false,
  placeholder = '',
  onChange,
  value,
  rows = null,      // for textarea
}) {
  const fieldMeta = useSelector(selectFieldMeta);
  const meta = fieldMeta[fieldName] || { source: 'empty', confidence: null };
  const isLocked = meta.source === 'locked';

  const stateClass = {
    ai: 'state-ai',
    uncertain: 'state-uncertain',
    corrected: 'state-corrected',
  }[meta.source] || '';

  const isRequired = required && !value;

  const badgeLabel = {
    ai: '✦ AI',
    uncertain: '⚠ Uncertain',
    corrected: '✓ Edited',
    locked: '🔒 Locked',
  }[meta.source];

  const badgeClass = {
    ai: 'ai',
    uncertain: 'uncertain',
    corrected: 'corrected',
    locked: 'missing',
  }[meta.source];

  const effectiveClass = [
    isRequired ? 'state-missing' : stateClass,
  ].filter(Boolean).join(' ');

  const commonProps = {
    id,
    name: fieldName,
    value: value || '',
    disabled: disabled || isLocked,
    placeholder: placeholder || `Enter ${label.toLowerCase()}`,
    onChange: (e) => onChange && onChange(fieldName, e.target.value),
    className: ['form-input', effectiveClass].filter(Boolean).join(' '),
  };

  return (
    <div className="form-field">
      <label className="form-label" htmlFor={id}>
        {label}
        {required && <span className="form-label-required">*</span>}
        {badgeLabel && meta.source !== 'empty' && (
          <span className={`field-state-badge ${badgeClass}`}>{badgeLabel}</span>
        )}
      </label>

      {options ? (
        <select
          {...commonProps}
          className={['form-select', effectiveClass].filter(Boolean).join(' ')}
        >
          <option value="">Select {label.toLowerCase()}</option>
          {options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      ) : rows ? (
        <textarea
          {...commonProps}
          rows={rows}
          className={['form-textarea', effectiveClass].filter(Boolean).join(' ')}
          style={{ height: 'auto', minHeight: `${rows * 24}px` }}
        />
      ) : (
        <input {...commonProps} type={type} />
      )}

      {meta.source === 'uncertain' && meta.confidence !== null && (
        <p className="text-xs" style={{ color: 'var(--color-warning)', marginTop: '2px' }}>
          Low confidence ({Math.round((meta.confidence || 0) * 100)}%) — please verify
        </p>
      )}
      {isRequired && (
        <p className="text-xs" style={{ color: 'var(--color-error)', marginTop: '2px' }}>
          Required — not provided in complaint
        </p>
      )}
    </div>
  );
}
