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

/**
 * Format a signal_date for display. Signal dates are often date-only
 * ("2026-02-24") with no time, so relative formatting ("23 hours ago")
 * is misleading. Instead show "Today", "Yesterday", or "Feb 24".
 */
export function formatSignalDate(dateStr: string): string {
  try {
    const isDateOnly = /^\d{4}-\d{2}-\d{2}$/.test(dateStr.trim());
    if (isDateOnly) {
      const today = new Date();
      const todayStr = today.toISOString().slice(0, 10);
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      const yesterdayStr = yesterday.toISOString().slice(0, 10);

      if (dateStr === todayStr) return "Today";
      if (dateStr === yesterdayStr) return "Yesterday";
      return format(parseISO(dateStr), "MMM d");
    }
    // Has a time component — use relative formatting
    const date = parseUTC(dateStr);
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
