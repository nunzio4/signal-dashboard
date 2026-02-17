import { formatDistanceToNow, parseISO, format } from "date-fns";

export function formatRelativeDate(dateStr: string): string {
  try {
    const date = parseISO(dateStr);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return dateStr;
  }
}

export function formatShortDate(dateStr: string): string {
  try {
    const date = parseISO(dateStr);
    return format(date, "MMM d");
  } catch {
    return dateStr;
  }
}

export function formatScore(score: number): string {
  return score.toFixed(1);
}

export function formatPct(pct: number): string {
  return `${pct.toFixed(0)}%`;
}
