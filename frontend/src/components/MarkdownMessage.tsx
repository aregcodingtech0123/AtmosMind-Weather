import React from 'react';
import { cn } from '../utils/cn';
import { stripHtmlTags } from '../utils/sanitize';

function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

interface MarkdownMessageProps {
  content: string;
  className?: string;
}

/**
 * Renders assistant Markdown tuned for AtmosMind chat/advice panels:
 * bold headings on their own line, paragraphs, and simple bullet lists.
 */
export const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content, className }) => {
  const safeContent = stripHtmlTags(content);
  const blocks = safeContent.trim().split(/\n\n+/).filter(Boolean);

  return (
    <div className={cn('space-y-3 text-sm leading-relaxed', className)}>
      {blocks.map((block, blockIndex) => {
        const trimmed = block.trim();
        const isStandaloneHeading = /^\*\*.+\*\*$/.test(trimmed) && !trimmed.includes('\n');

        if (isStandaloneHeading) {
          return (
            <p key={blockIndex} className="font-semibold text-white">
              {trimmed.slice(2, -2)}
            </p>
          );
        }

        const lines = trimmed.split('\n').filter((line) => line.trim());
        const isBulletList = lines.length > 0 && lines.every((line) => /^[-*]\s+/.test(line.trim()));

        if (isBulletList) {
          return (
            <ul key={blockIndex} className="list-disc list-inside space-y-1 text-white/90">
              {lines.map((line, lineIndex) => (
                <li key={lineIndex}>{renderInline(line.trim().replace(/^[-*]\s+/, ''))}</li>
              ))}
            </ul>
          );
        }

        return (
          <div key={blockIndex} className="space-y-1.5 text-white/90">
            {lines.map((line, lineIndex) => (
              <p key={lineIndex}>{renderInline(line)}</p>
            ))}
          </div>
        );
      })}
    </div>
  );
};
