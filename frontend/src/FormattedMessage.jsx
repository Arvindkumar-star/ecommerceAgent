import React, { useState } from 'react';

/**
 * Parses inline markdown:
 * - Bold: **text**
 * - Italic: *text* or _text_
 * - Inline code: `text`
 * - Citations: (`file.pdf`, Page X) or *(Source: ...)*
 */
function renderInlineMarkdown(text) {
  if (!text) return null;

  // Split tokens by bold, inline code, source citations
  // Regex pattern matching:
  // 1. Citations like `(sample.pdf, Page 1)` or *(Source: ...)*
  // 2. Bold: **...**
  // 3. Inline code: `...`
  // 4. Italics: *...*
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*\([^)]+\)\*|\((?:`?[^)]+\.(?:pdf|docx|txt|csv)`?[^)]*)\)|\*[^*]+\*)/g;
  const parts = text.split(pattern);

  return parts.map((part, i) => {
    if (!part) return null;

    // Bold
    if (part.startsWith('**') && part.endsWith('**')) {
      const inner = part.slice(2, -2);
      return (
        <strong key={i} className="fmt-strong">
          {inner}
        </strong>
      );
    }

    // Source Citation in parens, e.g. (`sample_company_policy.pdf`, Page 1) or *(Source: ...)*
    if (
      (part.startsWith('(') && part.endsWith(')') && (part.includes('.pdf') || part.includes('.docx') || part.includes('.txt') || part.includes('Page'))) ||
      (part.startsWith('*(') && part.endsWith(')*'))
    ) {
      const clean = part.replace(/^(\*\()?|\)?\*?$/g, '').replace(/[`()]/g, '').trim();
      return (
        <span key={i} className="source-citation-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <span>{clean}</span>
        </span>
      );
    }

    // Inline Code
    if (part.startsWith('`') && part.endsWith('`')) {
      const inner = part.slice(1, -1);
      // If looks like a document filename, render as file pill
      if (inner.endsWith('.pdf') || inner.endsWith('.docx') || inner.endsWith('.txt')) {
        return (
          <span key={i} className="doc-pill">
            📄 {inner}
          </span>
        );
      }
      return (
        <code key={i} className="inline-code">
          {inner}
        </code>
      );
    }

    // Italic
    if (part.startsWith('*') && part.endsWith('*') && !part.startsWith('**')) {
      const inner = part.slice(1, -1);
      return <em key={i} className="fmt-italic">{inner}</em>;
    }

    return part;
  });
}

/**
 * FormattedMessage Component:
 * Transforms raw LLM answers into high-end structured enterprise UI.
 */
export default function FormattedMessage({ content, isUser = false }) {
  const [copied, setCopied] = useState(false);

  if (isUser) {
    return <div className="user-message-content">{content}</div>;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Pre-process lines into blocks:
  // - Headings (#, ##, ###)
  // - Tables (| ... |)
  // - Blockquotes (> ...)
  // - Lists with nested items
  // - Regular paragraphs
  const lines = content ? content.split('\n') : [];
  const blocks = [];
  let currentList = null;
  let currentTable = null;

  const flushList = () => {
    if (currentList) {
      blocks.push({ type: 'list', items: currentList });
      currentList = null;
    }
  };

  const flushTable = () => {
    if (currentTable) {
      blocks.push({ type: 'table', rows: currentTable });
      currentTable = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (!trimmed) {
      flushList();
      flushTable();
      continue;
    }

    // Check for markdown table row
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      flushList();
      // Ignore divider lines like |---|---|
      if (/^\|[\s\-:|]+\|$/.test(trimmed)) {
        continue;
      }
      const cells = trimmed
        .slice(1, -1)
        .split('|')
        .map((c) => c.trim());
      if (!currentTable) currentTable = [];
      currentTable.push(cells);
      continue;
    } else {
      flushTable();
    }

    // Headings
    if (trimmed.startsWith('### ')) {
      flushList();
      blocks.push({ type: 'h3', text: trimmed.slice(4) });
      continue;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      blocks.push({ type: 'h2', text: trimmed.slice(3) });
      continue;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      blocks.push({ type: 'h1', text: trimmed.slice(2) });
      continue;
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      flushList();
      blocks.push({ type: 'quote', text: trimmed.slice(2) });
      continue;
    }

    // Divider
    if (trimmed === '---' || trimmed === '***') {
      flushList();
      blocks.push({ type: 'divider' });
      continue;
    }

    // Bullet or numbered list item
    // Matches "* ", "- ", "1. ", or indented variants like "  * "
    const listMatch = rawLine.match(/^(\s*)([*+-]|\d+\.)\s+(.*)$/);
    if (listMatch) {
      const indent = listMatch[1].length;
      const text = listMatch[3];
      if (!currentList) currentList = [];
      currentList.push({ indent, text });
      continue;
    }

    flushList();
    blocks.push({ type: 'p', text: trimmed });
  }

  flushList();
  flushTable();

  return (
    <div className="formatted-answer-container">
      {/* Action Header / Top Bar for Assistant Answer */}
      <div className="answer-header-meta">
        <div className="agent-tag">
          <span className="agent-indicator-dot" />
          <span className="agent-tag-name">NexusCX Enterprise Agent</span>
        </div>
        <button
          className="btn-copy-answer"
          onClick={handleCopy}
          title="Copy response to clipboard"
        >
          {copied ? (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span style={{ color: '#10b981' }}>Copied</span>
            </>
          ) : (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Render Blocks */}
      <div className="answer-body">
        {blocks.map((b, idx) => {
          if (b.type === 'h1') {
            return (
              <h1 key={idx} className="fmt-h1">
                {renderInlineMarkdown(b.text)}
              </h1>
            );
          }
          if (b.type === 'h2') {
            return (
              <h2 key={idx} className="fmt-h2">
                <span className="fmt-h-bar" />
                {renderInlineMarkdown(b.text)}
              </h2>
            );
          }
          if (b.type === 'h3') {
            return (
              <h3 key={idx} className="fmt-h3">
                <span className="fmt-h-dot" />
                {renderInlineMarkdown(b.text)}
              </h3>
            );
          }
          if (b.type === 'p') {
            return (
              <p key={idx} className="fmt-p">
                {renderInlineMarkdown(b.text)}
              </p>
            );
          }
          if (b.type === 'quote') {
            return (
              <div key={idx} className="fmt-callout">
                <div className="fmt-callout-icon">💡</div>
                <div className="fmt-callout-body">{renderInlineMarkdown(b.text)}</div>
              </div>
            );
          }
          if (b.type === 'divider') {
            return <div key={idx} className="fmt-divider" />;
          }
          if (b.type === 'table') {
            const [headerRow, ...bodyRows] = b.rows;
            return (
              <div key={idx} className="fmt-table-wrapper">
                <table className="fmt-table">
                  {headerRow && (
                    <thead>
                      <tr>
                        {headerRow.map((cell, cIdx) => (
                          <th key={cIdx}>{renderInlineMarkdown(cell)}</th>
                        ))}
                      </tr>
                    </thead>
                  )}
                  <tbody>
                    {bodyRows.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {row.map((cell, cIdx) => (
                          <td key={cIdx}>{renderInlineMarkdown(cell)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }
          if (b.type === 'list') {
            // Group items into top-level cards or structured items
            return (
              <div key={idx} className="fmt-list-group">
                {b.items.map((item, itemIdx) => {
                  const isIndented = item.indent > 0;
                  // Detect key-value patterns: **Label:** rest of line
                  const kvMatch = item.text.match(/^\*\*([^*:]+):\*\*\s*(.*)$/);

                  if (kvMatch) {
                    const label = kvMatch[1].trim();
                    const value = kvMatch[2].trim();

                    // Specific styling for important policy tags
                    const isWarning =
                      label.toLowerCase().includes('non-returnable') ||
                      label.toLowerCase().includes('ineligible') ||
                      label.toLowerCase().includes('warning');
                    const isFee = label.toLowerCase().includes('restocking') || label.toLowerCase().includes('fee');

                    return (
                      <div
                        key={itemIdx}
                        className={`fmt-kv-item ${isIndented ? 'fmt-kv-sub' : ''} ${
                          isWarning ? 'fmt-kv-warning' : ''
                        } ${isFee ? 'fmt-kv-fee' : ''}`}
                      >
                        <div className="fmt-kv-bullet">
                          <span className="fmt-bullet-dot" />
                        </div>
                        <div className="fmt-kv-content">
                          <span className="fmt-kv-label">{label}:</span>{' '}
                          <span className="fmt-kv-val">{renderInlineMarkdown(value)}</span>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={itemIdx}
                      className={`fmt-list-item ${isIndented ? 'fmt-list-sub' : ''}`}
                    >
                      <div className="fmt-bullet-dot" />
                      <div className="fmt-item-text">{renderInlineMarkdown(item.text)}</div>
                    </div>
                  );
                })}
              </div>
            );
          }
          return null;
        })}
      </div>
    </div>
  );
}
