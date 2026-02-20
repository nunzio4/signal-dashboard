import { formatRelativeDate } from "../../utils/formatting";

interface HeaderProps {
  lastIngestion: string | null;
  totalArticles: number;
  totalSignals: number;
  articles24h: number;
  signals24h: number;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function Header({
  lastIngestion,
  totalArticles,
  totalSignals,
  articles24h,
  signals24h,
  onRefresh,
  isRefreshing,
}: HeaderProps) {
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
        {lastIngestion && (
          <span className="last-refresh" title={lastIngestion}>
            Last fetch: {formatRelativeDate(lastIngestion)}
          </span>
        )}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="btn btn-outline refresh-btn"
          title="Refresh dashboard data"
        >
          {isRefreshing ? "⟳" : "↻"} Refresh
        </button>
      </div>
    </header>
  );
}
