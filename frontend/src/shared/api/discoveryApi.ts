import { apiClient } from "./client";
import type {
  DiscoveryGenerateResult,
  DiscoveryStream,
  DiscoveryStreamCopyFromMonitoringRequest,
  DiscoveryStreamCreateRequest,
  DiscoveryStreamUpdateRequest,
  FeedRecommendation,
  FeedRecommendationDecisionRequest,
  FeedRecommendationListResponse,
  FeedRecommendationSummary,
} from "../types/contracts";

const DISCOVERY_ENDPOINT = "/api/v1/discovery";

export type RecommendationFilters = {
  status?: "pending" | "accepted" | "denied" | "resolved_existing";
  q?: string;
  sort_by?: "created_at" | "updated_at" | "last_seen_at" | "decided_at" | "confidence" | "feed_title" | "status";
  sort_direction?: "asc" | "desc";
  limit?: number;
  offset?: number;
};

function buildRecommendationQuery(filters: RecommendationFilters): string {
  const params = new URLSearchParams();
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.q && filters.q.trim().length > 0) {
    params.set("q", filters.q.trim());
  }
  if (filters.sort_by) {
    params.set("sort_by", filters.sort_by);
  }
  if (filters.sort_direction) {
    params.set("sort_direction", filters.sort_direction);
  }
  if (typeof filters.limit === "number") {
    params.set("limit", String(filters.limit));
  }
  if (typeof filters.offset === "number") {
    params.set("offset", String(filters.offset));
  }
  const query = params.toString();
  return query.length > 0 ? `?${query}` : "";
}

export async function getDiscoveryStreams(): Promise<DiscoveryStream[]> {
  return apiClient.get<DiscoveryStream[]>(`${DISCOVERY_ENDPOINT}/streams`);
}

export async function createDiscoveryStream(payload: DiscoveryStreamCreateRequest): Promise<DiscoveryStream> {
  return apiClient.post<DiscoveryStreamCreateRequest, DiscoveryStream>(`${DISCOVERY_ENDPOINT}/streams`, payload);
}

export async function copyDiscoveryStreamFromMonitoring(
  payload: DiscoveryStreamCopyFromMonitoringRequest
): Promise<DiscoveryStream> {
  return apiClient.post<DiscoveryStreamCopyFromMonitoringRequest, DiscoveryStream>(
    `${DISCOVERY_ENDPOINT}/streams/copy-from-monitoring`,
    payload
  );
}

export async function updateDiscoveryStream(
  streamId: string,
  payload: DiscoveryStreamUpdateRequest
): Promise<DiscoveryStream> {
  return apiClient.patch<DiscoveryStreamUpdateRequest, DiscoveryStream>(
    `${DISCOVERY_ENDPOINT}/streams/${streamId}`,
    payload
  );
}

export async function deleteDiscoveryStream(streamId: string): Promise<void> {
  await apiClient.request<null>(`${DISCOVERY_ENDPOINT}/streams/${streamId}`, { method: "DELETE" });
}

export async function generateDiscoveryStream(
  streamId: string,
  payload: { max_results_per_query?: number; max_candidates?: number } = {}
): Promise<DiscoveryGenerateResult> {
  return apiClient.post<{ max_results_per_query?: number; max_candidates?: number }, DiscoveryGenerateResult>(
    `${DISCOVERY_ENDPOINT}/streams/${streamId}/generate`,
    payload
  );
}

export async function getFeedRecommendations(
  filters: RecommendationFilters = {}
): Promise<FeedRecommendationListResponse> {
  return apiClient.get<FeedRecommendationListResponse>(
    `${DISCOVERY_ENDPOINT}/recommendations${buildRecommendationQuery(filters)}`
  );
}

export async function decideFeedRecommendation(
  recommendationId: string,
  payload: FeedRecommendationDecisionRequest
): Promise<FeedRecommendation> {
  return apiClient.patch<FeedRecommendationDecisionRequest, FeedRecommendation>(
    `${DISCOVERY_ENDPOINT}/recommendations/${recommendationId}`,
    payload
  );
}

export async function resetFeedRecommendation(recommendationId: string): Promise<FeedRecommendation> {
  return apiClient.post<Record<string, never>, FeedRecommendation>(
    `${DISCOVERY_ENDPOINT}/recommendations/${recommendationId}/reset`,
    {}
  );
}

export async function getFeedRecommendationSummary(): Promise<FeedRecommendationSummary> {
  return apiClient.get<FeedRecommendationSummary>(`${DISCOVERY_ENDPOINT}/recommendations/summary`);
}
