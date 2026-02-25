import client from "./client";
import type { DashboardResponse, ManualSignalCreate, Signal, IngestionStatus, Source, DataSeries, DataSeriesWithData } from "../types";

export async function fetchDashboard(days: number = 270): Promise<DashboardResponse> {
  const { data } = await client.get<DashboardResponse>("/dashboard", {
    params: { days },
  });
  return data;
}

export async function createManualSignal(signal: ManualSignalCreate): Promise<Signal> {
  const { data } = await client.post<Signal>("/signals/manual", signal);
  return data;
}

export async function deleteSignal(signalId: number): Promise<void> {
  await client.delete(`/signals/${signalId}`);
}

export async function triggerIngestion(): Promise<unknown> {
  const { data } = await client.post("/ingest/run");
  return data;
}

export async function refreshAll(): Promise<unknown> {
  const { data } = await client.post("/ingest/refresh-all", null, {
    timeout: 5 * 60 * 1000,  // 5 minutes — fetches RSS + data series
  });
  return data;
}

export async function fetchIngestionStatus(): Promise<IngestionStatus> {
  const { data } = await client.get<IngestionStatus>("/ingest/status");
  return data;
}

// ── Sources / Feeds API ──

export async function fetchSources(): Promise<Source[]> {
  const { data } = await client.get<Source[]>("/sources");
  return data;
}

export interface CreateSourcePayload {
  name: string;
  source_type: "rss" | "newsapi" | "manual";
  url?: string;
  config?: string;
  enabled?: boolean;
}

export async function createSource(source: CreateSourcePayload): Promise<Source> {
  const { data } = await client.post<Source>("/sources", source);
  return data;
}

export interface UpdateSourcePayload {
  name?: string;
  url?: string;
  config?: string;
  enabled?: boolean;
}

export async function updateSource(sourceId: number, updates: UpdateSourcePayload): Promise<Source> {
  const { data } = await client.put<Source>(`/sources/${sourceId}`, updates);
  return data;
}

export async function deleteSource(sourceId: number): Promise<void> {
  await client.delete(`/sources/${sourceId}`);
}

// ── Data Series API ──

export async function fetchAllDataSeries(): Promise<DataSeries[]> {
  const { data } = await client.get<DataSeries[]>("/data-series");
  return data;
}

export async function fetchDataSeriesByThesis(thesisId: string, days = 365): Promise<DataSeriesWithData[]> {
  const { data } = await client.get<DataSeriesWithData[]>(`/data-series/by-thesis/${thesisId}`, {
    params: { days },
  });
  return data;
}

export async function triggerDataSeriesFetch(): Promise<unknown> {
  const { data } = await client.post("/data-series/fetch");
  return data;
}

// ── Analytics API (requires admin key on GET) ──

export interface AnalyticsLog {
  id: number;
  visitor_id: string;
  ip: string;
  path: string;
  user_agent: string;
  referer: string;
  referer_domain: string;
  timestamp: string;
}

export interface AnalyticsLogsResponse {
  period_hours: number;
  cutoff: string;
  count: number;
  logs: AnalyticsLog[];
}

export interface AnalyticsDigestResponse {
  period_hours: number;
  cutoff: string;
  unique_visitors: number;
  total_views: number;
  top_pages: { path: string; views: number; visitors: number }[];
  top_referrer_domains: { domain: string; views: number; visitors: number }[];
  top_referrer_urls: { url: string; visitors: number }[];
  hourly_breakdown: { hour: string; views: number; visitors: number }[];
  all_time: { unique_visitors: number; total_views: number };
}

export async function fetchAnalyticsLogs(hours: number, limit: number, apiKey: string): Promise<AnalyticsLogsResponse> {
  const { data } = await client.get<AnalyticsLogsResponse>("/analytics/logs", {
    params: { hours, limit },
    headers: { "X-API-Key": apiKey },
  });
  return data;
}

export async function fetchAnalyticsDigest(hours: number, apiKey: string): Promise<AnalyticsDigestResponse> {
  const { data } = await client.get<AnalyticsDigestResponse>("/analytics/digest", {
    params: { hours },
    headers: { "X-API-Key": apiKey },
  });
  return data;
}
