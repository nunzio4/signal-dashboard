export interface TrendPoint {
  date: string;
  score: number;
  count: number;
}

export interface Signal {
  id: number;
  thesis_id: string;
  direction: "supporting" | "weakening";
  strength: number;
  confidence: number;
  evidence_quote: string;
  reasoning: string;
  source_title: string | null;
  source_url: string | null;
  signal_date: string;
  is_manual: boolean;
  created_at: string | null;
}

export interface ThesisDashboardData {
  thesis_id: string;
  thesis_name: string;
  thesis_description: string;
  current_score: number;
  previous_score: number | null;
  score_trend: "rising" | "falling" | "stable";
  trend_data: TrendPoint[];
  recent_signals: Signal[];
  signal_count_7d: number;
  supporting_pct: number;
}

export interface DashboardResponse {
  theses: ThesisDashboardData[];
  last_ingestion: string | null;
  total_articles: number;
  total_signals: number;
}

export interface ManualSignalCreate {
  thesis_id: string;
  direction: "supporting" | "weakening";
  strength: number;
  evidence_quote: string;
  reasoning: string;
  source_title?: string;
  source_url?: string;
  signal_date?: string;
}

export interface Source {
  id: number;
  name: string;
  source_type: string;
  url: string | null;
  config: string | null;
  enabled: boolean;
  last_fetched_at: string | null;
  created_at: string;
}

export interface IngestionStatus {
  last_run: string | null;
  articles_total: number;
  articles_pending: number;
  articles_analyzed: number;
  sources_enabled: number;
}

// ── Data Series types ──

export interface DataPoint {
  date: string;
  value: number;
}

export interface DataSeriesWithData {
  id: string;
  name: string;
  description: string;
  unit: string;
  direction_logic: "higher_supporting" | "lower_supporting";
  provider: string;
  last_fetched_at: string | null;
  latest_value: number | null;
  previous_value: number | null;
  change_pct: number | null;
  points: DataPoint[];
}
