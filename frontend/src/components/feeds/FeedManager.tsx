import { useState } from "react";
import {
  useSources,
  useUpdateSource,
  useDeleteSource,
  useTriggerIngestion,
} from "../../hooks/useDashboard";
import { formatRelativeDate } from "../../utils/formatting";
import { AddFeedForm } from "./AddFeedForm";

export function FeedManager() {
  const [showAddForm, setShowAddForm] = useState(false);
  const { data: sources, isLoading, isError } = useSources();
  const updateSource = useUpdateSource();
  const deleteSourceMut = useDeleteSource();
  const triggerIngestion = useTriggerIngestion();

  const handleToggle = (id: number, currentEnabled: boolean) => {
    updateSource.mutate({ id, updates: { enabled: !currentEnabled } });
  };

  const handleDelete = (id: number, name: string) => {
    if (window.confirm(`Remove feed "${name}"? This won't delete any articles already ingested.`)) {
      deleteSourceMut.mutate(id);
    }
  };

  const handleRunIngestion = () => {
    triggerIngestion.mutate();
  };

  const sourceTypeLabel = (type: string) => {
    switch (type) {
      case "rss":
        return "RSS";
      case "newsapi":
        return "NewsAPI";
      case "manual":
        return "Manual";
      default:
        return type;
    }
  };

  return (
    <div className="feed-manager">
      <div className="feed-manager__header">
        <div>
          <h2 className="feed-manager__title">News Feeds</h2>
          <p className="feed-manager__subtitle">
            Manage RSS and news sources used for signal analysis
          </p>
        </div>
        <div className="feed-manager__actions">
          <button
            className="btn btn-outline"
            onClick={handleRunIngestion}
            disabled={triggerIngestion.isPending}
            title="Fetch new articles from all enabled feeds and run analysis"
          >
            {triggerIngestion.isPending ? "Ingesting..." : "Fetch & Analyze Now"}
          </button>
          <button
            className="btn btn-primary"
            onClick={() => setShowAddForm(true)}
          >
            + Add Feed
          </button>
        </div>
      </div>

      {triggerIngestion.isSuccess && (
        <div className="feed-notification feed-notification--success">
          Ingestion complete! New articles fetched and queued for analysis.
        </div>
      )}

      {showAddForm && (
        <div className="feed-add-section">
          <AddFeedForm onClose={() => setShowAddForm(false)} />
        </div>
      )}

      {isLoading && (
        <div className="loading-state" style={{ minHeight: 200 }}>
          <div className="spinner" />
          <p>Loading feeds...</p>
        </div>
      )}

      {isError && (
        <div className="form-error">Failed to load feeds. Is the backend running?</div>
      )}

      {sources && sources.length === 0 && (
        <div className="feed-empty">
          <p>No feeds configured yet.</p>
          <p className="text-muted">
            Add an RSS feed to start ingesting articles for analysis.
          </p>
        </div>
      )}

      {sources && sources.length > 0 && (
        <div className="feed-table-wrap">
          <table className="feed-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Name</th>
                <th>Type</th>
                <th>URL</th>
                <th>Last Fetched</th>
                <th>Added</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr
                  key={source.id}
                  className={!source.enabled ? "feed-row--disabled" : ""}
                >
                  <td>
                    <button
                      className={`feed-toggle ${source.enabled ? "feed-toggle--on" : "feed-toggle--off"}`}
                      onClick={() => handleToggle(source.id, source.enabled)}
                      title={source.enabled ? "Disable feed" : "Enable feed"}
                      disabled={updateSource.isPending}
                    >
                      <span className="feed-toggle__track">
                        <span className="feed-toggle__thumb" />
                      </span>
                    </button>
                  </td>
                  <td className="feed-name-cell">
                    <span className="feed-cell-name">{source.name}</span>
                  </td>
                  <td>
                    <span className={`feed-type-badge feed-type-badge--${source.source_type}`}>
                      {sourceTypeLabel(source.source_type)}
                    </span>
                  </td>
                  <td className="feed-url-cell">
                    {source.url ? (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="feed-url-link"
                        title={source.url}
                      >
                        {truncateUrl(source.url)}
                      </a>
                    ) : (
                      <span className="text-muted">-</span>
                    )}
                  </td>
                  <td className="text-muted">
                    {source.last_fetched_at
                      ? formatRelativeDate(source.last_fetched_at)
                      : "Never"}
                  </td>
                  <td className="text-muted">
                    {formatRelativeDate(source.created_at)}
                  </td>
                  <td>
                    <button
                      className="btn-icon btn-icon--danger"
                      onClick={() => handleDelete(source.id, source.name)}
                      disabled={deleteSourceMut.isPending}
                      title="Remove feed"
                    >
                      &times;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sources && (
        <div className="feed-summary">
          <span>
            {sources.filter((s) => s.enabled).length} of {sources.length} feeds
            enabled
          </span>
        </div>
      )}
    </div>
  );
}

function truncateUrl(url: string, maxLen = 55): string {
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
