import { formatRelativeDate } from "../../utils/formatting";

interface HeaderProps {
  lastIngestion: string | null;
  lastDataFetch: string | null;
  totalArticles: number;
  totalSignals: number;
  articles24h: number;
  signals24h: number;
  onRefresh: () => void;
  isRefreshing: boolean;
}

/** Return the more recent of two ISO timestamps (or whichever is non-null). */
function mostRecent(a: string | null, b: string | null): string | null {
  if (!a) return b;
  if (!b) return a;
  return a > b ? a : b;
}

export function Header({
  lastIngestion,
  lastDataFetch,
  totalArticles,
  totalSignals,
  articles24h,
  signals24h,
  onRefresh,
  isRefreshing,
}: HeaderProps) {
  const lastRefresh = mostRecent(lastIngestion, lastDataFetch);

  return (
    <header className="app-header">
      <div className="header-left">
        <h1 className="app-title">
          <span className="title-icon">◈</span> Signal Dashboard
        </h1>
        <p className="app-subtitle">Investment Thesis Monitor</p>
      </div>

      <div className="header-stats">
        <div className="header-stat-group">
          <span className="stat-group-label">Articles</span>
          <div className="stat-group-row">
            <div className="header-stat">
              <span className="stat-value">{totalArticles.toLocaleString()}</span>
              <span className="stat-label">All-time</span>
            </div>
            <div className="header-stat">
              <span className="stat-value stat-value--recent">{articles24h}</span>
              <span className="stat-label">Past 24h</span>
            </div>
          </div>
        </div>
        <div className="header-stat-group">
          <span className="stat-group-label">Signals</span>
          <div className="stat-group-row">
            <div className="header-stat">
              <span className="stat-value">{totalSignals.toLocaleString()}</span>
              <span className="stat-label">All-time</span>
            </div>
            <div className="header-stat">
              <span className="stat-value stat-value--recent">{signals24h}</span>
              <span className="stat-label">Past 24h</span>
            </div>
          </div>
        </div>
      </div>

      <div className="header-right">
        {lastRefresh && (
          <span className="last-refresh" title={lastRefresh}>
            Last refresh: {formatRelativeDate(lastRefresh)}
          </span>
        )}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="btn btn-outline refresh-btn"
          title="Refresh RSS feeds and data series"
        >
          {isRefreshing ? "⟳ Refreshing…" : "↻ Refresh"}
        </button>
      </div>
    </header>
  );
}
