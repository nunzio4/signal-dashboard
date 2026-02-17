/**
 * Maps signal strength (1-10) to a color.
 * 1-3: green (weak), 4-5: yellow (mild), 6-7: orange (moderate), 8-10: red (strong)
 */
export function getStrengthColor(strength: number): string {
  if (strength <= 3) return "#4ade80";
  if (strength <= 5) return "#facc15";
  if (strength <= 7) return "#fb923c";
  return "#ef4444";
}

/**
 * Maps a composite score (1-10) to a color for the gauge.
 */
export function getScoreColor(score: number): string {
  if (score <= 3) return "#4ade80";
  if (score <= 5) return "#facc15";
  if (score <= 7) return "#fb923c";
  return "#ef4444";
}

/**
 * Get a color for direction badges.
 */
export function getDirectionColor(direction: string): string {
  return direction === "supporting" ? "#22c55e" : "#ef4444";
}

/**
 * Thesis ID to an accent color for visual distinction.
 */
export function getThesisAccent(thesisId: string): string {
  const accents: Record<string, string> = {
    ai_job_displacement: "#818cf8",    // indigo
    ai_deflation: "#34d399",           // emerald
    datacenter_credit_crisis: "#f97316", // orange
  };
  return accents[thesisId] ?? "#6366f1";
}
