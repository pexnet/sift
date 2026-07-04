import type {
  DashboardDiscoveryCandidatesCard,
  DashboardFeedHealthCard,
  DashboardMonitoringSignalsCard,
  DashboardPrioritizedQueue,
  DashboardPriorityProfile,
  DashboardPriorityProfileUpdate,
  DashboardSavedFollowupCard,
  DashboardTrendsCard,
} from "../types/contracts";
import { apiClient } from "./client";

const DASHBOARD_ENDPOINT = "/api/v1/dashboard";

export async function getDashboardPrioritizedQueue(limit = 10): Promise<DashboardPrioritizedQueue> {
  return apiClient.get<DashboardPrioritizedQueue>(`${DASHBOARD_ENDPOINT}/cards/prioritized-queue?limit=${limit}`);
}

export async function getDashboardFeedHealth(): Promise<DashboardFeedHealthCard> {
  return apiClient.get<DashboardFeedHealthCard>(`${DASHBOARD_ENDPOINT}/cards/feed-health`);
}

export async function getDashboardSavedFollowup(limit = 5): Promise<DashboardSavedFollowupCard> {
  return apiClient.get<DashboardSavedFollowupCard>(`${DASHBOARD_ENDPOINT}/cards/saved-followup?limit=${limit}`);
}

export async function getDashboardMonitoringSignals(
  windowHours = 24
): Promise<DashboardMonitoringSignalsCard> {
  return apiClient.get<DashboardMonitoringSignalsCard>(
    `${DASHBOARD_ENDPOINT}/cards/monitoring-signals?window_hours=${windowHours}`
  );
}

export async function getDashboardDiscoveryCandidates(
  limit = 5
): Promise<DashboardDiscoveryCandidatesCard> {
  return apiClient.get<DashboardDiscoveryCandidatesCard>(
    `${DASHBOARD_ENDPOINT}/cards/discovery-candidates?limit=${limit}`
  );
}

export async function getDashboardTrends(
  windowHours = 24,
  baselineDays = 14
): Promise<DashboardTrendsCard> {
  return apiClient.get<DashboardTrendsCard>(
    `${DASHBOARD_ENDPOINT}/cards/trends?window_hours=${windowHours}&baseline_days=${baselineDays}`
  );
}

export async function getDashboardPriorityProfile(): Promise<DashboardPriorityProfile> {
  return apiClient.get<DashboardPriorityProfile>(`${DASHBOARD_ENDPOINT}/prioritization-profile`);
}

export async function updateDashboardPriorityProfile(
  payload: DashboardPriorityProfileUpdate
): Promise<DashboardPriorityProfile> {
  return apiClient.patch<DashboardPriorityProfileUpdate, DashboardPriorityProfile>(
    `${DASHBOARD_ENDPOINT}/prioritization-profile`,
    payload
  );
}