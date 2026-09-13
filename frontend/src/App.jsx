import React, { useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import Header from './components/Header';
import ComplaintWorkspace from './components/ComplaintWorkspace';
import { ToastContainer } from './components/Toast';
import { selectComplaintStatus, selectCommittedId } from './features/complaint/complaintSlice';

let toastIdCounter = 0;

export default function App() {
  const [toasts, setToasts] = useState([]);
  const status = useSelector(selectComplaintStatus);
  const committedId = useSelector(selectCommittedId);

  const addToast = useCallback((message, type = 'info') => {
    const id = ++toastIdCounter;
    setToasts(prev => [...prev, { id, message, type }]);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <div className="app-layout">
      <Header />
      <main className="app-main">
        <ComplaintWorkspace />
      </main>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
