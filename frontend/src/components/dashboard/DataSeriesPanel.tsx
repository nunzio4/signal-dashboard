import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { useDataSeriesByThesis } from "../../hooks/useDashboard";
import type { DataSeriesWithData } from "../../types";

interface DataSeriesPanelProps {
  thesisId: string;
  accentColor: string;
}

export function DataSeriesPanel({ thesisId, accentColor }: DataSeriesPanelProps) {
  const { data: seriesList, isLoading } = useDataSeriesByThesis(thesisId, 730);

  if (isLoading) {
    return (
      <div className="ds-panel ds-panel--loading">
        <div className="spinner" style={{ width: 24, height: 24 }} />
      </div>
    );
  }

  if (!seriesList || seriesList.length === 0) {
    return (
      <div className="ds-panel ds-panel--empty">
        <p className="text-muted">No data series available yet</p>
        <p className="text-muted" style={{ fontSize: "0.72rem" }}>
          Configure FRED/BLS API keys and trigger a data fetch
        </p>
      </div>
    );
  }

  // Only show series that have data points
  const withData = seriesList.filter((s) => s.points.length > 0);

  if (withData.length === 0) {
    return (
      <div className="ds-panel ds-panel--empty">
        <p className="text-muted">Data series configured but no data fetched yet</p>
      </div>
    );
  }

  return (
    <div className="ds-panel">
      <h4 className="ds-panel__title">Data Series Evidence</h4>
      <div className="ds-panel__grid">
        {withData.map((series) => (
          <DataSeriesCard key={series.id} series={series} accentColor={accentColor} />
        ))}
      </div>
    </div>
  );
}

function DataSeriesCard({
  series,
  accentColor,
}: {
  series: DataSeriesWithData;
  accentColor: string;
}) {
  const isSupporting = isChangeSupporting(series);
  const changeColor =
    isSupporting === null
      ? "var(--text-muted)"
      : isSupporting
        ? "var(--supporting)"
        : "var(--weakening)";

  // Format data for chart — take last 24 points for readability
  const chartData = series.points.slice(-24).map((p) => ({
    date: p.date,
    value: p.value,
  }));

  return (
    <div className="ds-card">
      <div className="ds-card__header">
        <div className="ds-card__info">
          <span className="ds-card__name">{series.name}</span>
          <span className="ds-card__provider">{providerLabel(series.provider)}</span>
        </div>
        <div className="ds-card__values">
          {series.latest_value !== null && (
            <span className="ds-card__latest">
              {formatValue(series.latest_value, series.unit)}
            </span>
          )}
          {series.change_pct !== null && (
            <span className="ds-card__change" style={{ color: changeColor }}>
              {series.change_pct > 0 ? "+" : ""}
              {series.change_pct.toFixed(1)}%
            </span>
          )}
        </div>
      </div>

      {chartData.length >= 2 && (
        <div className="ds-card__chart">
          <ResponsiveContainer width="100%" height={64}>
            <LineChart data={chartData}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--border)"
                vertical={false}
              />
              <XAxis dataKey="date" hide />
              <YAxis hide domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: "0.72rem",
                }}
                labelFormatter={(label) => String(label)}
                formatter={(value: number | undefined) => [
                  formatValue(value ?? 0, series.unit),
                  series.name,
                ]}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={accentColor}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <p className="ds-card__desc">{series.description}</p>
    </div>
  );
}

function isChangeSupporting(series: DataSeriesWithData): boolean | null {
  if (series.change_pct === null) return null;
  if (series.direction_logic === "higher_supporting") {
    return series.change_pct > 0;
  }
  return series.change_pct < 0;
}

function providerLabel(provider: string): string {
  switch (provider) {
    case "fred":
      return "FRED";
    case "bls":
      return "BLS";
    case "sec_edgar":
      return "SEC EDGAR";
    default:
      return provider.toUpperCase();
  }
}

function formatValue(value: number, unit: string): string {
  if (unit.includes("Billions")) return `$${value.toFixed(1)}B`;
  if (unit.includes("Millions")) return `$${(value / 1000).toFixed(1)}B`;
  if (unit.includes("Thousands")) return `${(value / 1000).toFixed(1)}M`;
  if (unit === "% Spread") return `${value.toFixed(2)}%`;
  if (unit === "Net %") return `${value.toFixed(1)}%`;
  if (unit === "Claims") return `${(value / 1000).toFixed(0)}K`;
  if (unit === "Index") return value.toFixed(1);
  return value.toLocaleString();
}
