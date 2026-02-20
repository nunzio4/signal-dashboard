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

const PREDICTION_PROVIDERS = new Set(["polymarket", "kalshi", "metaculus"]);

interface PredictionMarketPanelProps {
  thesisId: string;
  accentColor: string;
}

export function PredictionMarketPanel({
  thesisId,
  accentColor,
}: PredictionMarketPanelProps) {
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
        <p className="text-muted">No prediction market data yet</p>
      </div>
    );
  }

  // Only show prediction market series that have data points
  const predictionSeries = seriesList.filter(
    (s) => PREDICTION_PROVIDERS.has(s.provider) && s.points.length > 0
  );

  if (predictionSeries.length === 0) {
    return (
      <div className="ds-panel ds-panel--empty">
        <p className="text-muted">Prediction markets configured</p>
        <p className="text-muted" style={{ fontSize: "0.72rem" }}>
          Data will appear after the next fetch cycle
        </p>
      </div>
    );
  }

  return (
    <div className="ds-panel">
      <h4 className="ds-panel__title">Prediction Markets</h4>
      <div className="ds-panel__grid">
        {predictionSeries.map((series) => (
          <PredictionMarketCard
            key={series.id}
            series={series}
            accentColor={accentColor}
          />
        ))}
      </div>
    </div>
  );
}

function PredictionMarketCard({
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

  // Show all data points for the full history chart
  const chartData = series.points.map((p) => ({
    date: p.date,
    value: p.value,
  }));

  return (
    <div className="ds-card">
      <div className="ds-card__header">
        <div className="ds-card__info">
          <span className="ds-card__name">{series.name}</span>
          <span
            className={`ds-card__provider pm-provider pm-provider--${series.provider}`}
          >
            {providerLabel(series.provider)}
          </span>
        </div>
        <div className="ds-card__values">
          {series.latest_value !== null && (
            <span className="ds-card__latest">
              {series.latest_value.toFixed(1)}%
            </span>
          )}
          {series.change_pct !== null && (
            <span className="ds-card__change" style={{ color: changeColor }}>
              {series.change_pct > 0 ? "+" : ""}
              {series.change_pct.toFixed(1)}pts
              <span className="ds-card__change-period"> 30d</span>
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
              <YAxis hide domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: "0.72rem",
                }}
                labelFormatter={(label) => String(label)}
                formatter={(value: number | undefined) => [
                  `${(value ?? 0).toFixed(1)}%`,
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
    case "polymarket":
      return "POLYMARKET";
    case "kalshi":
      return "KALSHI";
    case "metaculus":
      return "METACULUS";
    default:
      return provider.toUpperCase();
  }
}
