import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

export function Toast({ toast, onDismiss }) {
  const timerRef = useRef(null);

  useEffect(() => {
    timerRef.current = setTimeout(() => onDismiss(toast.id), 5000);
    return () => clearTimeout(timerRef.current);
  }, [toast.id, onDismiss]);

  return (
    <div className={`toast ${toast.type || 'info'}`} role="alert">
      <span className="toast-message">{toast.message}</span>
      <button className="toast-close" onClick={() => onDismiss(toast.id)} aria-label="Dismiss" type="button">✕</button>
    </div>
  );
}

export function ToastContainer({ toasts, onDismiss }) {
  return createPortal(
    <div className="toast-container">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>,
    document.body
  );
}
