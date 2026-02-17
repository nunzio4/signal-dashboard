import type { Signal } from "../../types";
import { EvidenceCard } from "./EvidenceCard";

interface EvidenceListProps {
  signals: Signal[];
}

export function EvidenceList({ signals }: EvidenceListProps) {
  if (signals.length === 0) {
    return (
      <div className="evidence-list-empty">
        <p>No signals recorded yet</p>
        <p className="text-muted">Use the form below to add manual signals, or configure data sources for automatic ingestion.</p>
      </div>
    );
  }

  return (
    <div className="evidence-list">
      <h4 className="evidence-list-title">Recent Evidence ({signals.length})</h4>
      <div className="evidence-scroll">
        {signals.map((signal) => (
          <EvidenceCard key={signal.id} signal={signal} />
        ))}
      </div>
    </div>
  );
}
