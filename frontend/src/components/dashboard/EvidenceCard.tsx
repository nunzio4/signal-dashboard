import type { Signal } from "../../types";
import { getStrengthColor, getDirectionColor } from "../../utils/colors";
import { formatRelativeDate } from "../../utils/formatting";

interface EvidenceCardProps {
  signal: Signal;
}

export function EvidenceCard({ signal }: EvidenceCardProps) {
  const strengthColor = getStrengthColor(signal.strength);
  const dirColor = getDirectionColor(signal.direction);

  return (
    <div className="evidence-card">
      <div className="evidence-header">
        <span
          className="strength-pip"
          style={{ backgroundColor: strengthColor }}
          title={`Strength: ${signal.strength}/10`}
        >
          {signal.strength}
        </span>
        <span
          className="direction-tag"
          style={{ color: dirColor, borderColor: dirColor }}
        >
          {signal.direction === "supporting" ? "▲ Supporting" : "▼ Weakening"}
        </span>
        {signal.is_manual && <span className="manual-badge">Manual</span>}
        <time className="evidence-date" title={signal.signal_date}>
          {formatRelativeDate(signal.signal_date)}
        </time>
      </div>

      <blockquote className="evidence-quote">
        "{signal.evidence_quote}"
      </blockquote>

      <p className="evidence-reasoning">{signal.reasoning}</p>

      {signal.source_url && (
        <a
          href={signal.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="evidence-source"
        >
          {signal.source_title || "View Source"} →
        </a>
      )}
      {!signal.source_url && signal.source_title && (
        <span className="evidence-source-text">{signal.source_title}</span>
      )}
    </div>
  );
}
