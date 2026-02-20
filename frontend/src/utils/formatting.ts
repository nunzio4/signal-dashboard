import { formatDistanceToNow, parseISO, format } from "date-fns";

/** Parse a backend timestamp (UTC but without trailing Z) into a Date. */
function parseUTC(dateStr: string): Date {
  // Backend returns "2026-02-20 03:35:04" (UTC, no Z). Append Z so
  // parseISO treats it as UTC rather than local time.
  const normalized = dateStr.includes("T") ? dateStr : dateStr.replace(" ", "T");
  return parseISO(normalized.endsWith("Z") ? normalized : normalized + "Z");
}

export function formatRelativeDate(dateStr: string): string {
  try {
    const date = parseUTC(dateStr);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return dateStr;
  }
}

/** Format a backend UTC timestamp as a local absolute time, e.g. "Feb 20, 3:35 PM". */
export function formatAbsoluteDate(dateStr: string): string {
  try {
    const date = parseUTC(dateStr);
    return format(date, "MMM d, h:mm a");
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
