import type {
  Feed,
  FeedHealthListResponse,
  FeedHealthQueryParams,
  FeedLifecycleResult,
  FeedLifecycleUpdateRequest,
  FeedSettingsUpdateRequest,
} from "../types/contracts";
import { apiClient } from "./client";

const FEEDS_ENDPOINT = "/api/v1/feeds";

function toFeedHealthSearchParams(params: FeedHealthQueryParams): URLSearchParams {
  const searchParams = new URLSearchParams();

  if (params.lifecycle) {
    searchParams.set("lifecycle", params.lifecycle);
  }
  if (params.q) {
    searchParams.set("q", params.q);
  }
  if (params.stale_only !== undefined) {
    searchParams.set("stale_only", String(params.stale_only));
  }
  if (params.error_only !== undefined) {
    searchParams.set("error_only", String(params.error_only));
  }
  if (params.limit !== undefined) {
    searchParams.set("limit", String(params.limit));
  }
  if (params.offset !== undefined) {
    searchParams.set("offset", String(params.offset));
  }

  return searchParams;
}

export async function getFeedHealth(params: FeedHealthQueryParams): Promise<FeedHealthListResponse> {
  const searchParams = toFeedHealthSearchParams(params);
  const path = searchParams.toString().length > 0 ? `${FEEDS_ENDPOINT}/health?${searchParams.toString()}` : `${FEEDS_ENDPOINT}/health`;
  return apiClient.get<FeedHealthListResponse>(path);
}

export async function updateFeedSettings(feedId: string, payload: FeedSettingsUpdateRequest): Promise<Feed> {
  return apiClient.patch<FeedSettingsUpdateRequest, Feed>(`${FEEDS_ENDPOINT}/${feedId}/settings`, payload);
}

export async function updateFeedLifecycle(feedId: string, payload: FeedLifecycleUpdateRequest): Promise<FeedLifecycleResult> {
  return apiClient.patch<FeedLifecycleUpdateRequest, FeedLifecycleResult>(`${FEEDS_ENDPOINT}/${feedId}/lifecycle`, payload);
}
