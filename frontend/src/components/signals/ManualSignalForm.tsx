import { useState } from "react";
import { useCreateSignal } from "../../hooks/useDashboard";
import type { ManualSignalCreate } from "../../types";

interface ManualSignalFormProps {
  theses: Array<{ thesis_id: string; thesis_name: string }>;
}

export function ManualSignalForm({ theses }: ManualSignalFormProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [thesisId, setThesisId] = useState(theses[0]?.thesis_id ?? "");
  const [direction, setDirection] = useState<"supporting" | "weakening">("supporting");
  const [strength, setStrength] = useState(5);
  const [evidenceQuote, setEvidenceQuote] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");

  const mutation = useCreateSignal();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!evidenceQuote.trim() || !reasoning.trim()) return;

    const signal: ManualSignalCreate = {
      thesis_id: thesisId,
      direction,
      strength,
      evidence_quote: evidenceQuote.trim(),
      reasoning: reasoning.trim(),
      source_title: sourceTitle.trim() || undefined,
      source_url: sourceUrl.trim() || undefined,
    };

    mutation.mutate(signal, {
      onSuccess: () => {
        setEvidenceQuote("");
        setReasoning("");
        setSourceTitle("");
        setSourceUrl("");
        setStrength(5);
        setIsOpen(false);
      },
    });
  };

  if (!isOpen) {
    return (
      <div className="manual-signal-toggle">
        <button onClick={() => setIsOpen(true)} className="btn btn-primary">
          + Add Manual Signal
        </button>
      </div>
    );
  }

  return (
    <form className="manual-signal-form" onSubmit={handleSubmit}>
      <div className="form-header">
        <h3>Add Manual Signal</h3>
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          className="btn-close"
        >
          ✕
        </button>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="thesis">Thesis</label>
          <select
            id="thesis"
            value={thesisId}
            onChange={(e) => setThesisId(e.target.value)}
          >
            {theses.map((t) => (
              <option key={t.thesis_id} value={t.thesis_id}>
                {t.thesis_name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Direction</label>
          <div className="direction-toggle">
            <button
              type="button"
              className={`toggle-btn ${direction === "supporting" ? "active supporting" : ""}`}
              onClick={() => setDirection("supporting")}
            >
              ▲ Supporting
            </button>
            <button
              type="button"
              className={`toggle-btn ${direction === "weakening" ? "active weakening" : ""}`}
              onClick={() => setDirection("weakening")}
            >
              ▼ Weakening
            </button>
          </div>
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="strength">
          Strength: <strong>{strength}</strong> / 10
        </label>
        <input
          type="range"
          id="strength"
          min={1}
          max={10}
          value={strength}
          onChange={(e) => setStrength(Number(e.target.value))}
          className="strength-slider"
        />
        <div className="strength-labels">
          <span>Weak</span>
          <span>Moderate</span>
          <span>Strong</span>
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="evidence">Evidence Quote *</label>
        <textarea
          id="evidence"
          placeholder="Key excerpt or data point that supports your assessment..."
          value={evidenceQuote}
          onChange={(e) => setEvidenceQuote(e.target.value)}
          rows={3}
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="reasoning">Reasoning *</label>
        <textarea
          id="reasoning"
          placeholder="Why does this constitute a signal for this thesis?"
          value={reasoning}
          onChange={(e) => setReasoning(e.target.value)}
          rows={2}
          required
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="source-title">Source Title</label>
          <input
            type="text"
            id="source-title"
            placeholder="e.g., Bloomberg, Company 10-K..."
            value={sourceTitle}
            onChange={(e) => setSourceTitle(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="source-url">Source URL</label>
          <input
            type="url"
            id="source-url"
            placeholder="https://..."
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
          />
        </div>
      </div>

      <div className="form-actions">
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          className="btn btn-secondary"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={mutation.isPending || !evidenceQuote.trim() || !reasoning.trim()}
        >
          {mutation.isPending ? "Saving..." : "Add Signal"}
        </button>
      </div>

      {mutation.isError && (
        <div className="form-error">
          Error: {(mutation.error as Error).message}
        </div>
      )}
    </form>
  );
}
