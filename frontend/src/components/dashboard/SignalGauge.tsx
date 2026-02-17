import { useMemo } from "react";
import { getScoreColor } from "../../utils/colors";
import { formatScore } from "../../utils/formatting";

interface SignalGaugeProps {
  score: number;
  trend: "rising" | "falling" | "stable";
  previousScore: number | null;
  accent: string;
}

/**
 * SVG-based radial gauge showing composite thesis signal strength (1-10).
 * Custom built — no external gauge library dependency.
 */
export function SignalGauge({ score, trend, previousScore, accent: _accent }: SignalGaugeProps) {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2 + 10;
  const radius = 75;
  const strokeWidth = 14;

  // Arc goes from 220° to 320° (a 220-degree sweep)
  const startAngle = -220;
  const endAngle = 40;
  const totalAngle = endAngle - startAngle;

  const scoreColor = getScoreColor(score);

  const { valueArc, needleAngle } = useMemo(() => {
    const normalizedScore = Math.max(1, Math.min(10, score));
    const fraction = (normalizedScore - 1) / 9;

    const toRad = (deg: number) => (deg * Math.PI) / 180;

    // Background arc (full sweep)
    const bgStart = toRad(startAngle);
    const bgEnd = toRad(endAngle);
    const bgX1 = cx + radius * Math.cos(bgStart);
    const bgY1 = cy + radius * Math.sin(bgStart);
    const bgX2 = cx + radius * Math.cos(bgEnd);
    const bgY2 = cy + radius * Math.sin(bgEnd);
    const bgLargeArc = totalAngle > 180 ? 1 : 0;
    const bgPath = `M ${bgX1} ${bgY1} A ${radius} ${radius} 0 ${bgLargeArc} 1 ${bgX2} ${bgY2}`;

    // Value arc
    const valEndAngle = startAngle + totalAngle * fraction;
    const valEnd = toRad(valEndAngle);
    const valX2 = cx + radius * Math.cos(valEnd);
    const valY2 = cy + radius * Math.sin(valEnd);
    const valSweep = totalAngle * fraction;
    const valLargeArc = valSweep > 180 ? 1 : 0;
    const valPath = `M ${bgX1} ${bgY1} A ${radius} ${radius} 0 ${valLargeArc} 1 ${valX2} ${valY2}`;

    // Needle angle (degrees for SVG transform)
    const needle = startAngle + totalAngle * fraction;

    return { bgArc: bgPath, valueArc: valPath, needleAngle: needle };
  }, [score, cx, cy, radius]);

  const delta = previousScore != null ? score - previousScore : null;
  const trendIcon = trend === "rising" ? "▲" : trend === "falling" ? "▼" : "●";
  const trendColor =
    trend === "rising" ? "#22c55e" : trend === "falling" ? "#ef4444" : "#64748b";

  // Arc segment colors for the background
  const arcSegments = useMemo(() => {
    const toRad = (deg: number) => (deg * Math.PI) / 180;
    const segments = [
      { from: 0, to: 0.222, color: "#4ade8040" },   // 1-3: green
      { from: 0.222, to: 0.444, color: "#facc1540" }, // 3-5: yellow
      { from: 0.444, to: 0.667, color: "#fb923c40" }, // 5-7: orange
      { from: 0.667, to: 1.0, color: "#ef444440" },   // 7-10: red
    ];

    return segments.map((seg) => {
      const sAngle = startAngle + totalAngle * seg.from;
      const eAngle = startAngle + totalAngle * seg.to;
      const sRad = toRad(sAngle);
      const eRad = toRad(eAngle);
      const x1 = cx + radius * Math.cos(sRad);
      const y1 = cy + radius * Math.sin(sRad);
      const x2 = cx + radius * Math.cos(eRad);
      const y2 = cy + radius * Math.sin(eRad);
      const sweep = eAngle - sAngle;
      const large = sweep > 180 ? 1 : 0;
      return {
        path: `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`,
        color: seg.color,
      };
    });
  }, [cx, cy, radius]);

  return (
    <div className="signal-gauge">
      <svg viewBox={`0 0 ${size} ${size - 20}`} width="100%" style={{ maxWidth: 220 }}>
        {/* Background colored arc segments */}
        {arcSegments.map((seg, i) => (
          <path
            key={i}
            d={seg.path}
            fill="none"
            stroke={seg.color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        ))}

        {/* Value arc */}
        <path
          d={valueArc}
          fill="none"
          stroke={scoreColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          style={{
            filter: `drop-shadow(0 0 6px ${scoreColor}80)`,
            transition: "d 0.6s ease-in-out",
          }}
        />

        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={cx + 50 * Math.cos((needleAngle * Math.PI) / 180)}
          y2={cy + 50 * Math.sin((needleAngle * Math.PI) / 180)}
          stroke="var(--text-primary)"
          strokeWidth={2}
          strokeLinecap="round"
          style={{ transition: "all 0.6s ease-in-out" }}
        />
        <circle cx={cx} cy={cy} r={4} fill="var(--text-primary)" />

        {/* Score text */}
        <text
          x={cx}
          y={cy + 35}
          textAnchor="middle"
          fill={scoreColor}
          fontSize="28"
          fontWeight="700"
          fontFamily="inherit"
        >
          {formatScore(score)}
        </text>

        {/* Scale labels */}
        <text x={20} y={cy + 20} fontSize="11" fill="var(--text-secondary)" textAnchor="middle">
          1
        </text>
        <text x={size - 20} y={cy + 20} fontSize="11" fill="var(--text-secondary)" textAnchor="middle">
          10
        </text>
      </svg>

      {/* Trend indicator */}
      <div className="gauge-trend" style={{ color: trendColor }}>
        <span className="trend-icon">{trendIcon}</span>
        <span className="trend-label" style={{ textTransform: "capitalize" }}>
          {trend}
        </span>
        {delta != null && (
          <span className="trend-delta">
            ({delta > 0 ? "+" : ""}
            {delta.toFixed(1)})
          </span>
        )}
      </div>
    </div>
  );
}
