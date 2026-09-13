import React, { useEffect, useRef, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  selectMessages, selectIsProcessing, selectCurrentStage,
  selectStageIndex, selectInputMode, selectCopilotError,
  setInputMode,
} from '../features/copilot/copilotSlice';
import {
  selectComplaintFields, selectRisk, selectComplaintStatus,
  sendCopilotFollowUp,
} from '../features/complaint/complaintSlice';
import { mapReduxFieldsToApi } from '../features/complaint/complaintSlice';
import CopilotMessage from './CopilotMessage';
import ExtractionProgress from './ExtractionProgress';
import RiskAssessmentCard from './RiskAssessmentCard';
import UploadDropzone from './UploadDropzone';
import TextComplaintInput from './TextComplaintInput';

export default function CopilotPanel() {
  const dispatch = useDispatch();
  const messages = useSelector(selectMessages);
  const isProcessing = useSelector(selectIsProcessing);
  const currentStage = useSelector(selectCurrentStage);
  const stageIndex = useSelector(selectStageIndex);
  const inputMode = useSelector(selectInputMode);
  const error = useSelector(selectCopilotError);
  const complaintFields = useSelector(selectComplaintFields);
  const risk = useSelector(selectRisk);
  const status = useSelector(selectComplaintStatus);

  const [composerText, setComposerText] = useState('');
  const messagesEndRef = useRef(null);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  function handleComposerSend() {
    const msg = composerText.trim();
    if (!msg || isProcessing) return;
    setComposerText('');

    const apiFields = mapReduxFieldsToApi(complaintFields);
    const apiRisk = risk?.severity ? {
      category: risk.category,
      severity: risk.severity,
      priority: risk.priority,
      rationale: risk.rationale,
      suggested_next_action: risk.suggestedNextAction,
    } : null;

    dispatch(sendCopilotFollowUp({
      message: msg,
      currentComplaint: apiFields,
      currentRisk: apiRisk,
    }));
  }

  function handleComposerKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleComposerSend();
    }
  }

  const showRisk = risk && risk.severity && (status === 'review' || status === 'committed');
  const isLocked = status === 'committed';
  const hasMessages = messages.length > 0;

  const copilotStatusText = isProcessing
    ? 'Analyzing…'
    : status === 'review'
    ? 'Review required'
    : status === 'committed'
    ? 'Complaint committed'
    : 'Ready';

  return (
    <div className="panel copilot-panel">
      {/* Header */}
      <div className="copilot-header">
        <div className="copilot-avatar">✦</div>
        <div className="copilot-title-block">
          <div className="copilot-title">AI Complaint Intake Assistant</div>
          <div className="copilot-status-text">{copilotStatusText}</div>
        </div>
      </div>

      {/* Input Mode Tabs — only show before committed */}
      {!isLocked && !hasMessages && (
        <div className="mode-tabs">
          <button
            className={`mode-tab ${inputMode === 'upload' ? 'active' : ''}`}
            onClick={() => dispatch(setInputMode('upload'))}
            type="button"
          >
            📎 Upload Document
          </button>
          <button
            className={`mode-tab ${inputMode === 'text' ? 'active' : ''}`}
            onClick={() => dispatch(setInputMode('text'))}
            type="button"
          >
            ✏ Paste Text
          </button>
        </div>
      )}

      {/* Upload / Text Input area — only show before analysis */}
      {!hasMessages && !isProcessing && !isLocked && (
        <div style={{ padding: '16px 20px' }}>
          {inputMode === 'upload' ? <UploadDropzone /> : <TextComplaintInput />}
        </div>
      )}

      {/* Processing progress */}
      {isProcessing && (
        <div style={{ padding: '12px 20px' }}>
          <ExtractionProgress currentStage={currentStage} stageIndex={stageIndex} />
        </div>
      )}

      {/* Messages area */}
      {hasMessages && (
        <div className="messages-area">
          {messages.map((msg) => (
            <CopilotMessage key={msg.id} message={msg} />
          ))}

          {isProcessing && (
            <div className="message assistant">
              <div className="message-avatar">AI</div>
              <div className="message-bubble" style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <span className="spinner" />
                <span className="text-sm text-muted">Analyzing…</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Empty state */}
      {!hasMessages && !isProcessing && (
        <div className="copilot-empty">
          <div className="copilot-empty-icon">✦</div>
          <div className="copilot-empty-title">AI Complaint Intake Assistant</div>
          <div className="copilot-empty-text">
            Upload a complaint document or paste complaint text to begin AI extraction.
          </div>
        </div>
      )}

      {/* Risk Assessment Card */}
      {showRisk && (
        <div style={{ padding: '0 20px 16px' }}>
          <RiskAssessmentCard risk={risk} />
        </div>
      )}

      {/* Error display */}
      {error && (
        <div style={{ padding: '0 20px 12px' }}>
          <div className="completeness-banner error">
            <span className="completeness-icon">⚠</span>
            <div className="completeness-text">
              <div className="completeness-title">AI Error</div>
              <div className="completeness-fields">{error}</div>
            </div>
          </div>
        </div>
      )}

      {/* Composer — for corrections after initial analysis */}
      {hasMessages && !isLocked && (
        <div className="copilot-composer">
          <textarea
            id="copilot-composer"
            className="composer-input"
            value={composerText}
            onChange={(e) => setComposerText(e.target.value)}
            onKeyDown={handleComposerKeyDown}
            placeholder="Correct a field or ask a question… e.g. 'The batch number is BMX240602'"
            rows={1}
            disabled={isProcessing}
            aria-label="Correction input"
          />
          <button
            className="composer-send"
            onClick={handleComposerSend}
            disabled={isProcessing || !composerText.trim()}
            aria-label="Send correction"
            type="button"
          >
            {isProcessing ? <span className="spinner" style={{ borderColor: 'white', borderRightColor: 'transparent' }} /> : '↑'}
          </button>
        </div>
      )}
    </div>
  );
}
