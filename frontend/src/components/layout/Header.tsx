import { formatAbsoluteDate, formatRelativeDate } from "../../utils/formatting";

interface HeaderProps {
  lastIngestion: string | null;
  lastDataFetch: string | null;
  nextIngestion: string | null;
  nextDataFetch: string | null;
  totalArticles: number;
  articles24h: number;
  totalDataPoints: number;
  dataPoints24h: number;
  totalNewsSignals: number;
  newsSignals24h: number;
  totalDataSignals: number;
  dataSignals24h: number;
  predictionMarketSeries: number;
}

/** Return the more recent of two ISO timestamps (or whichever is non-null). */
function mostRecent(a: string | null, b: string | null): string | null {
  if (!a) return b;
  if (!b) return a;
  return a > b ? a : b;
}

/** Return the earliest of two ISO timestamps (or whichever is non-null). */
function earliest(a: string | null, b: string | null): string | null {
  if (!a) return b;
  if (!b) return a;
  return a < b ? a : b;
}

export function Header({
  lastIngestion,
  lastDataFetch,
  nextIngestion,
  nextDataFetch,
  totalArticles,
  articles24h,
  totalDataPoints,
  dataPoints24h,
  totalNewsSignals,
  newsSignals24h,
  totalDataSignals,
  dataSignals24h,
  predictionMarketSeries,
}: HeaderProps) {
  const lastRefresh = mostRecent(lastIngestion, lastDataFetch);
  const nextRefresh = earliest(nextIngestion, nextDataFetch);

  return (
    <header className="app-header">
      <div className="header-left">
        <h1 className="app-title">
          <span className="title-icon">&#9672;</span> Signal Dashboard
        </h1>
        <p className="app-subtitle">Investment Thesis Monitor</p>
      </div>

      <div className="header-stats">
        {/* News pipeline: Articles -> News Signals */}
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
          <span className="stat-group-label">News Signals</span>
          <div className="stat-group-row">
            <div className="header-stat">
              <span className="stat-value">{totalNewsSignals.toLocaleString()}</span>
              <span className="stat-label">All-time</span>
            </div>
            <div className="header-stat">
              <span className="stat-value stat-value--recent">{newsSignals24h}</span>
              <span className="stat-label">Past 24h</span>
            </div>
          </div>
        </div>

        <div className="header-stats-separator" />

        {/* Data pipeline: Data Points -> Data Signals */}
        <div className="header-stat-group">
          <span className="stat-group-label">Data Points</span>
          <div className="stat-group-row">
            <div className="header-stat">
              <span className="stat-value">{totalDataPoints.toLocaleString()}</span>
              <span className="stat-label">All-time</span>
            </div>
            <div className="header-stat">
              <span className="stat-value stat-value--recent">{dataPoints24h}</span>
              <span className="stat-label">Past 24h</span>
            </div>
          </div>
        </div>
        <div className="header-stat-group">
          <span className="stat-group-label">Data Signals</span>
          <div className="stat-group-row">
            <div className="header-stat">
              <span className="stat-value">{totalDataSignals.toLocaleString()}</span>
              <span className="stat-label">All-time</span>
            </div>
            <div className="header-stat">
              <span className="stat-value stat-value--recent">{dataSignals24h}</span>
              <span className="stat-label">Past 24h</span>
            </div>
          </div>
        </div>

        <div className="header-stats-separator" />

        {/* Prediction Markets */}
        <div className="header-stat-group">
          <span className="stat-group-label">Prediction Markets</span>
          <div className="stat-group-row">
            <div className="header-stat">
              <span className="stat-value">{predictionMarketSeries}</span>
              <span className="stat-label">Markets</span>
            </div>
          </div>
        </div>
      </div>

      <div className="header-right">
        {lastRefresh && (
          <span
            className="header-timestamp"
            title={formatRelativeDate(lastRefresh)}
          >
            Last ingestion: {formatAbsoluteDate(lastRefresh)}
          </span>
        )}
        {nextRefresh && (
          <span
            className="header-timestamp header-timestamp--next"
            title={formatRelativeDate(nextRefresh)}
          >
            Next ingestion: {formatAbsoluteDate(nextRefresh)}
          </span>
        )}
      </div>
    </header>
  );
}
