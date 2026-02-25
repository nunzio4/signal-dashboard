import { useState, useEffect } from "react";
import { getAdminKey } from "../../api/client";
import {
  fetchAnalyticsLogs,
  fetchAnalyticsDigest,
  type AnalyticsLog,
  type AnalyticsDigestResponse,
} from "../../api/dashboard";
import { formatAbsoluteDate } from "../../utils/formatting";

type TimeWindow = "1" | "24" | "168" | "720";

const WINDOW_LABELS: Record<TimeWindow, string> = {
  "1": "Last Hour",
  "24": "Last 24 Hours",
  "168": "Last 7 Days",
  "720": "Last 30 Days",
};

export function AnalyticsPage() {
  const [window, setWindow] = useState<TimeWindow>("24");
  const [logs, setLogs] = useState<AnalyticsLog[]>([]);
  const [digest, setDigest] = useState<AnalyticsDigestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    const key = getAdminKey();
    if (!key) {
      setError("Admin API key is required to view analytics.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const hours = parseInt(window);
      const [logsRes, digestRes] = await Promise.all([
        fetchAnalyticsLogs(hours, 500, key),
        fetchAnalyticsDigest(hours, key),
      ]);
      setLogs(logsRes.logs);
      setDigest(digestRes);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { status?: number } };
        if (axiosErr.response?.status === 403) {
          setError("Invalid API key. Please reload and try again.");
        } else {
          setError("Failed to load analytics data.");
        }
      } else {
        setError("Failed to load analytics data.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [window]);

  /** Parse user agent into a short readable label. */
  function shortUA(ua: string): string {
    if (!ua) return "—";
    let browser = "Unknown";
    if (ua.includes("Chrome") && !ua.includes("Edg")) browser = "Chrome";
    else if (ua.includes("Firefox")) browser = "Firefox";
    else if (ua.includes("Safari") && !ua.includes("Chrome")) browser = "Safari";
    else if (ua.includes("Edg")) browser = "Edge";
    let os = "";
    if (ua.includes("Windows")) os = "Windows";
    else if (ua.includes("Mac OS")) os = "Mac";
    else if (ua.includes("Linux")) os = "Linux";
    else if (ua.includes("iPhone")) os = "iPhone";
    else if (ua.includes("Android")) os = "Android";
    return os ? `${browser} / ${os}` : browser;
  }

  return (
    <div className="analytics-page">
      <div className="analytics-page__header">
        <div>
          <h2 className="analytics-page__title">Visitor Analytics</h2>
          <p className="analytics-page__subtitle">
            Page views and visitor activity
          </p>
        </div>
        <div className="analytics-page__controls">
          <select
            className="analytics-select"
            value={window}
            onChange={(e) => setWindow(e.target.value as TimeWindow)}
          >
            {Object.entries(WINDOW_LABELS).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
          <button
            className="btn btn-primary btn-sm"
            onClick={loadData}
            disabled={loading}
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && <div className="analytics-error">{error}</div>}

      {digest && (
        <div className="analytics-summary">
          <div className="analytics-stat">
            <span className="analytics-stat__value">{digest.unique_visitors}</span>
            <span className="analytics-stat__label">Unique Visitors</span>
          </div>
          <div className="analytics-stat">
            <span className="analytics-stat__value">{digest.total_views}</span>
            <span className="analytics-stat__label">Page Views</span>
          </div>
          <div className="analytics-stat">
            <span className="analytics-stat__value">{digest.all_time.unique_visitors}</span>
            <span className="analytics-stat__label">All-Time Visitors</span>
          </div>
          <div className="analytics-stat">
            <span className="analytics-stat__value">{digest.all_time.total_views}</span>
            <span className="analytics-stat__label">All-Time Views</span>
          </div>
        </div>
      )}

      {digest && digest.top_referrer_domains.length > 0 && (
        <div className="analytics-section">
          <h3 className="analytics-section__title">Top Referrer Domains</h3>
          <div className="analytics-mini-table">
            {digest.top_referrer_domains.map((d) => (
              <div key={d.domain} className="analytics-mini-row">
                <span className="analytics-mini-row__label">{d.domain}</span>
                <span className="analytics-mini-row__value">
                  {d.visitors} visitor{d.visitors !== 1 ? "s" : ""}, {d.views} view{d.views !== 1 ? "s" : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="analytics-section">
        <h3 className="analytics-section__title">
          Visitor Log ({logs.length} entries)
        </h3>
        {logs.length === 0 && !loading && (
          <p className="text-muted">No visits recorded in this time window.</p>
        )}
        {logs.length > 0 && (
          <div className="analytics-table-wrap">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Visitor</th>
                  <th>IP</th>
                  <th>Path</th>
                  <th>Referrer</th>
                  <th>Device</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="analytics-table__time">
                      {formatAbsoluteDate(log.timestamp)}
                    </td>
                    <td className="analytics-table__mono">{log.visitor_id}</td>
                    <td className="analytics-table__mono">{log.ip}</td>
                    <td>{log.path}</td>
                    <td>{log.referer_domain || "—"}</td>
                    <td>{shortUA(log.user_agent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
