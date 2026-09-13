import React from 'react';

export default function FormSection({ number, title, children }) {
  return (
    <section className="form-section">
      <div className="form-section-header">
        <span className="form-section-number">{number}</span>
        <h3 className="form-section-title">{title}</h3>
      </div>
      {children}
    </section>
  );
}
