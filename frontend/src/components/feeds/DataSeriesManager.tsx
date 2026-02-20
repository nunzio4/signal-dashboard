import { useState } from "react";
import { useAllDataSeries } from "../../hooks/useDashboard";
import { formatRelativeDate } from "../../utils/formatting";

export function DataSeriesManager() {
  const { data: series, isLoading, isError } = useAllDataSeries();
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyUrl = (url: string, id: string) => {
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  const providerLabel = (provider: string) => {
    switch (provider) {
      case "fred":
        return "FRED";
      case "bls":
        return "BLS";
      case "sec_edgar":
        return "SEC EDGAR";
      default:
        return provider;
    }
  };

  const thesisLabel = (thesisId: string) => {
    switch (thesisId) {
      case "ai_job_displacement":
        return "AI Job Displacement";
      case "ai_deflation":
        return "AI Deflation";
      case "datacenter_credit_crisis":
        return "Datacenter Credit Crisis";
      default:
        return thesisId;
    }
  };

  // Group series by thesis
  const grouped = series
    ? series.reduce<Record<string, typeof series>>((acc, s) => {
        (acc[s.thesis_id] = acc[s.thesis_id] || []).push(s);
        return acc;
      }, {})
    : {};

  const thesisOrder = [
    "ai_job_displacement",
    "ai_deflation",
    "datacenter_credit_crisis",
  ];

  return (
    <div className="feed-manager">
      <div className="feed-manager__header">
        <div>
          <h2 className="feed-manager__title">Data Series</h2>
          <p className="feed-manager__subtitle">
            Structured data sources used for data signal generation
          </p>
        </div>
      </div>

      {isLoading && (
        <div className="loading-state" style={{ minHeight: 200 }}>
          <div className="spinner" />
          <p>Loading data series...</p>
        </div>
      )}

      {isError && (
        <div className="form-error">
          Failed to load data series. Is the backend running?
        </div>
      )}

      {series && series.length === 0 && (
        <div className="feed-empty">
          <p>No data series configured yet.</p>
        </div>
      )}

      {series && series.length > 0 &&
        thesisOrder.map((thesisId) => {
          const items = grouped[thesisId];
          if (!items || items.length === 0) return null;
          return (
            <div key={thesisId} className="ds-thesis-group">
              <h3 className="ds-thesis-group__title">
                {thesisLabel(thesisId)}
              </h3>
              <div className="feed-table-wrap">
                <table className="feed-table">
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Name</th>
                      <th>Description</th>
                      <th>Provider</th>
                      <th>Source</th>
                      <th>Last Fetched</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((s) => (
                      <tr
                        key={s.id}
                        className={!s.enabled ? "feed-row--disabled" : ""}
                      >
                        <td>
                          <span
                            className={`ds-status-dot ${s.enabled ? "ds-status-dot--on" : "ds-status-dot--off"}`}
                            title={s.enabled ? "Enabled" : "Disabled"}
                          />
                        </td>
                        <td className="feed-name-cell">
                          <span className="feed-cell-name">{s.name}</span>
                          <span className="ds-unit">{s.unit}</span>
                        </td>
                        <td className="ds-description-cell">
                          <span className="ds-description">{s.description}</span>
                        </td>
                        <td>
                          <span
                            className={`feed-type-badge feed-type-badge--${s.provider}`}
                          >
                            {providerLabel(s.provider)}
                          </span>
                        </td>
                        <td className="feed-url-cell">
                          {s.source_url ? (
                            <span className="ds-source-link-wrap">
                              <a
                                href={s.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="feed-url-link"
                                title={s.source_url}
                              >
                                {truncateUrl(s.source_url)}
                              </a>
                              <button
                                className="ds-copy-btn"
                                onClick={() =>
                                  handleCopyUrl(s.source_url!, s.id)
                                }
                                title="Copy link"
                              >
                                {copiedId === s.id ? "\u2713" : "\u2398"}
                              </button>
                            </span>
                          ) : (
                            <span className="text-muted">-</span>
                          )}
                        </td>
                        <td className="text-muted">
                          {s.last_fetched_at
                            ? formatRelativeDate(s.last_fetched_at)
                            : "Never"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}

      {series && (
        <div className="feed-summary">
          <span>
            {series.filter((s) => s.enabled).length} of {series.length} series
            enabled
          </span>
        </div>
      )}
    </div>
  );
}

function truncateUrl(url: string, maxLen = 45): string {
  try {
    const u = new URL(url);
    const display = u.hostname + u.pathname;
    return display.length > maxLen
      ? display.slice(0, maxLen - 1) + "\u2026"
      : display;
  } catch {
    return url.length > maxLen ? url.slice(0, maxLen - 1) + "\u2026" : url;
  }
}
