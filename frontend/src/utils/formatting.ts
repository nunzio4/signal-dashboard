import { formatDistanceToNow, parseISO, format } from "date-fns";

/** Detect the user's IANA timezone, falling back to America/New_York. */
function getUserTimezone(): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return tz || "America/New_York";
  } catch {
    return "America/New_York";
  }
}

/** Format a Date as a localized string with timezone, e.g. "Feb 25, 3:35 PM EST". */
function formatWithTz(date: Date): string {
  try {
    const tz = getUserTimezone();
    const formatted = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZoneName: "short",
    }).format(date);
    return formatted;
  } catch {
    return format(date, "MMM d, h:mm a");
  }
}

/** Format a Date as a full datetime with timezone, e.g. "Feb 25, 2026 3:35 PM EST". */
function formatFullWithTz(date: Date): string {
  try {
    const tz = getUserTimezone();
    const formatted = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZoneName: "short",
    }).format(date);
    return formatted;
  } catch {
    return format(date, "MMM d, yyyy h:mm a");
  }
}

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

/** Format a backend UTC timestamp as a local absolute time with timezone, e.g. "Feb 20, 3:35 PM EST". */
export function formatAbsoluteDate(dateStr: string): string {
  try {
    const date = parseUTC(dateStr);
    return formatWithTz(date);
  } catch {
    return dateStr;
  }
}

/**
 * Format a signal's timestamp for display.
 *
 * Accepts either:
 *  - A full datetime (created_at / ingestion time) → "Feb 25, 2026 3:35 PM EST"
 *  - A date-only string (signal_date) → "Today", "Yesterday", or "Feb 24"
 */
export function formatSignalDate(dateStr: string): string {
  try {
    const isDateOnly = /^\d{4}-\d{2}-\d{2}$/.test(dateStr.trim());
    if (isDateOnly) {
      const tz = getUserTimezone();
      const today = new Date(
        new Date().toLocaleDateString("en-CA", { timeZone: tz })
      );
      const todayStr = today.toISOString().slice(0, 10);
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      const yesterdayStr = yesterday.toISOString().slice(0, 10);

      if (dateStr === todayStr) return "Today";
      if (dateStr === yesterdayStr) return "Yesterday";
      return format(parseISO(dateStr), "MMM d");
    }
    // Has a time component — show full datetime with timezone
    const date = parseUTC(dateStr);
    return formatFullWithTz(date);
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
