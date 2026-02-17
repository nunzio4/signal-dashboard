import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchDashboard,
  createManualSignal,
  deleteSignal,
  triggerIngestion,
  fetchSources,
  createSource,
  updateSource,
  deleteSource,
} from "../api/dashboard";
import type { ManualSignalCreate } from "../types";
import type { CreateSourcePayload, UpdateSourcePayload } from "../api/dashboard";

export function useDashboardData(days: number = 30) {
  return useQuery({
    queryKey: ["dashboard", days],
    queryFn: () => fetchDashboard(days),
    refetchInterval: 5 * 60 * 1000,    // Auto-refresh every 5 minutes
    staleTime: 2 * 60 * 1000,          // Stale after 2 minutes
  });
}

export function useCreateSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (signal: ManualSignalCreate) => createManualSignal(signal),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (signalId: number) => deleteSignal(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useTriggerIngestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => triggerIngestion(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

// ── Sources / Feeds hooks ──

export function useSources() {
  return useQuery({
    queryKey: ["sources"],
    queryFn: fetchSources,
    staleTime: 60 * 1000,
  });
}

export function useCreateSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (source: CreateSourcePayload) => createSource(source),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}

export function useUpdateSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, updates }: { id: number; updates: UpdateSourcePayload }) =>
      updateSource(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}

export function useDeleteSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: number) => deleteSource(sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}
