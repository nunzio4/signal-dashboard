import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { TrendPoint } from "../../types";
import { formatShortDate } from "../../utils/formatting";

interface TrendChartProps {
  data: TrendPoint[];
  accent: string;
}

export function TrendChart({ data, accent }: TrendChartProps) {
  if (data.length === 0) {
    return (
      <div className="trend-chart-empty">
        <p>No trend data yet</p>
        <p className="text-muted">Add signals to see the trend chart</p>
      </div>
    );
  }

  return (
    <div className="trend-chart">
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${accent.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={accent} stopOpacity={0.3} />
              <stop offset="95%" stopColor={accent} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tickFormatter={formatShortDate}
            tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            minTickGap={30}
          />
          <YAxis
            domain={[1, 10]}
            ticks={[1, 3, 5, 7, 10]}
            tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              color: "var(--text-primary)",
              fontSize: 13,
            }}
            labelFormatter={(label) => formatShortDate(String(label))}
            formatter={(value) => [Number(value).toFixed(1), "Score"]}
          />
          <ReferenceLine
            y={5.5}
            stroke="var(--text-secondary)"
            strokeDasharray="4 4"
            strokeOpacity={0.4}
          />
          <Area
            type="monotone"
            dataKey="score"
            stroke={accent}
            strokeWidth={2}
            fill={`url(#grad-${accent.replace("#", "")})`}
            dot={{ r: 3, fill: accent, strokeWidth: 0 }}
            activeDot={{ r: 5, fill: accent, stroke: "var(--bg-card)", strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
