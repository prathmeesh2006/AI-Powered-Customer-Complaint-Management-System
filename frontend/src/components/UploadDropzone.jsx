import React, { useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { analyzeComplaintFile } from '../features/complaint/complaintSlice';

const ACCEPTED = '.pdf,.txt,.text';
const MAX_MB = 10;

export default function UploadDropzone() {
  const dispatch = useDispatch();
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  function handleFile(file) {
    if (!file) return;
    if (file.size > MAX_MB * 1024 * 1024) {
      alert(`File too large. Maximum size is ${MAX_MB} MB.`);
      return;
    }
    const lower = file.name.toLowerCase();
    if (!lower.endsWith('.pdf') && !lower.endsWith('.txt') && !lower.endsWith('.text')) {
      alert('Only PDF and plain text files are supported.');
      return;
    }
    setSelectedFile(file);
    dispatch(analyzeComplaintFile(file));
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }

  function handleInputChange(e) {
    const file = e.target.files[0];
    handleFile(file);
  }

  function handleRemove() {
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = '';
  }

  if (selectedFile) {
    return (
      <div className="upload-file-selected">
        <span style={{ fontSize: '18px' }}>📄</span>
        <span className="upload-file-name">{selectedFile.name}</span>
        <span className="text-xs text-muted">
          {(selectedFile.size / 1024).toFixed(0)} KB
        </span>
        <button
          className="btn btn-sm btn-secondary"
          onClick={handleRemove}
          title="Remove file"
          type="button"
        >
          ✕
        </button>
      </div>
    );
  }

  return (
    <div
      className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      aria-label="Upload complaint document"
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        onChange={handleInputChange}
        aria-label="Choose complaint file"
        tabIndex={-1}
      />
      <div className="upload-zone-icon">📎</div>
      <p className="upload-zone-text">
        Drag & drop a complaint document here or{' '}
        <span className="upload-zone-link">browse</span>
      </p>
      <p className="upload-zone-hint">PDF or plain text • Max {MAX_MB} MB</p>
    </div>
  );
}
