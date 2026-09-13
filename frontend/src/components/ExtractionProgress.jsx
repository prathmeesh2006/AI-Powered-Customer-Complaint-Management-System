import React from 'react';
import { PROCESSING_STAGES } from '../features/copilot/copilotSlice';

export default function ExtractionProgress({ currentStage, stageIndex }) {
  if (!currentStage) return null;

  return (
    <div className="extraction-progress">
      <div className="text-xs font-semibold" style={{ color: 'var(--color-primary)', marginBottom: '8px' }}>
        Analyzing complaint…
      </div>
      {PROCESSING_STAGES.map((stage, idx) => {
        const isDone = idx < stageIndex;
        const isActive = idx === stageIndex;
        const stateClass = isDone ? 'done' : isActive ? 'active' : 'pending';

        return (
          <div key={stage.id} className={`progress-stage ${stateClass}`}>
            <span className={`progress-stage-icon ${stateClass}`}>
              {isDone ? '✓' : isActive ? '…' : '·'}
            </span>
            <span className="progress-stage-label">{stage.label}</span>
          </div>
        );
      })}
    </div>
  );
}
