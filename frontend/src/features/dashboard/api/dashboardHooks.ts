import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getDashboardDiscoveryCandidates,
  getDashboardFeedHealth,
  getDashboardMonitoringSignals,
  getDashboardPrioritizedQueue,
  getDashboardPriorityProfile,
  getDashboardSavedFollowup,
  getDashboardTrends,
  updateDashboardPriorityProfile,
} from "../../../shared/api/dashboardApi";
import { queryKeys } from "../../../shared/api/queryKeys";
import type { DashboardPriorityProfileUpdate } from "../../../shared/types/contracts";

export function useDashboardPrioritizedQueueQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardPrioritizedQueue(),
    queryFn: () => getDashboardPrioritizedQueue(10),
    enabled,
  });
}

export function useDashboardFeedHealthQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardFeedHealth(),
    queryFn: getDashboardFeedHealth,
    enabled,
  });
}

export function useDashboardSavedFollowupQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardSavedFollowup(),
    queryFn: () => getDashboardSavedFollowup(5),
    enabled,
  });
}

export function useDashboardMonitoringSignalsQuery(windowHours = 24, enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardMonitoringSignals(windowHours),
    queryFn: () => getDashboardMonitoringSignals(windowHours),
    enabled,
  });
}

export function useDashboardDiscoveryCandidatesQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardDiscoveryCandidates(),
    queryFn: () => getDashboardDiscoveryCandidates(5),
    enabled,
  });
}

export function useDashboardTrendsQuery(windowHours = 24, baselineDays = 14, enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardTrends(windowHours, baselineDays),
    queryFn: () => getDashboardTrends(windowHours, baselineDays),
    enabled,
  });
}

export function useDashboardPriorityProfileQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardPriorityProfile(),
    queryFn: getDashboardPriorityProfile,
    enabled,
  });
}

export function useUpdateDashboardPriorityProfileMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DashboardPriorityProfileUpdate) => updateDashboardPriorityProfile(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboardPriorityProfile() });
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboardPrioritizedQueue() });
    },
  });
}