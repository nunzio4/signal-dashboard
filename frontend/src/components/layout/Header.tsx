import { formatRelativeDate } from "../../utils/formatting";

interface HeaderProps {
  lastIngestion: string | null;
  totalArticles: number;
  totalSignals: number;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function Header({
  lastIngestion,
  totalArticles,
  totalSignals,
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
        <div className="header-stat">
          <span className="stat-value">{totalArticles}</span>
          <span className="stat-label">Articles</span>
        </div>
        <div className="header-stat">
          <span className="stat-value">{totalSignals}</span>
          <span className="stat-label">Signals</span>
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
