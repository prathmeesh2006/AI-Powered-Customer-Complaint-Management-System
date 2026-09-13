import React from 'react';

/**
 * Individual message bubble in the copilot conversation.
 * Renders **bold** text using a simple markdown-like parser.
 */
function renderContent(content) {
  if (!content) return null;

  // Simple **bold** and *italic* rendering
  const parts = content.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

export default function CopilotMessage({ message }) {
  const { role, content, timestamp } = message;
  const isUser = role === 'user';
  const initials = isUser ? 'U' : 'AI';

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar" title={isUser ? 'You' : 'AI Copilot'}>
        {initials}
      </div>
      <div className="message-bubble">
        {renderContent(content)}
        {timestamp && (
          <div style={{
            fontSize: '10px',
            opacity: 0.5,
            marginTop: '4px',
            textAlign: isUser ? 'right' : 'left',
          }}>
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        )}
      </div>
    </div>
  );
}
