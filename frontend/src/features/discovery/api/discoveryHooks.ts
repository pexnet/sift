import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createDiscoveryStream,
  decideFeedRecommendation,
  deleteDiscoveryStream,
  generateDiscoveryStream,
  getDiscoveryStreams,
  getFeedRecommendations,
  getFeedRecommendationSummary,
  resetFeedRecommendation,
  type RecommendationFilters,
  updateDiscoveryStream,
} from "../../../shared/api/discoveryApi";
import { queryKeys } from "../../../shared/api/queryKeys";
import type {
  DiscoveryStreamCreateRequest,
  DiscoveryStreamUpdateRequest,
  FeedRecommendationDecisionRequest,
} from "../../../shared/types/contracts";

function normalizeRecommendationFilters(filters: RecommendationFilters) {
  return {
    status: filters.status ?? "all",
    q: filters.q ?? "",
    sort_by: filters.sort_by ?? "updated_at",
    sort_direction: filters.sort_direction ?? "desc",
    limit: filters.limit ?? 50,
    offset: filters.offset ?? 0,
  } as const;
}

async function invalidateDiscoveryQueries(queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.discoveryStreams() }),
    queryClient.invalidateQueries({ queryKey: ["discovery", "recommendations"] }),
    queryClient.invalidateQueries({ queryKey: queryKeys.discoverySummary() }),
    queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
  ]);
}

export function useDiscoveryStreamsQuery() {
  return useQuery({
    queryKey: queryKeys.discoveryStreams(),
    queryFn: getDiscoveryStreams,
  });
}

export function useCreateDiscoveryStreamMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DiscoveryStreamCreateRequest) => createDiscoveryStream(payload),
    onSuccess: async () => invalidateDiscoveryQueries(queryClient),
  });
}

export function useUpdateDiscoveryStreamMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ streamId, payload }: { streamId: string; payload: DiscoveryStreamUpdateRequest }) =>
      updateDiscoveryStream(streamId, payload),
    onSuccess: async () => invalidateDiscoveryQueries(queryClient),
  });
}

export function useDeleteDiscoveryStreamMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (streamId: string) => deleteDiscoveryStream(streamId),
    onSuccess: async () => invalidateDiscoveryQueries(queryClient),
  });
}

export function useGenerateDiscoveryStreamMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      streamId,
      payload,
    }: {
      streamId: string;
      payload?: { max_results_per_query?: number; max_candidates?: number };
    }) => generateDiscoveryStream(streamId, payload),
    onSuccess: async () => invalidateDiscoveryQueries(queryClient),
  });
}

export function useFeedRecommendationsQuery(filters: RecommendationFilters) {
  const normalized = normalizeRecommendationFilters(filters);
  return useQuery({
    queryKey: queryKeys.discoveryRecommendations(normalized),
    queryFn: () => getFeedRecommendations(filters),
  });
}

export function useFeedRecommendationSummaryQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.discoverySummary(),
    queryFn: getFeedRecommendationSummary,
    enabled,
  });
}

export function useDecideFeedRecommendationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      recommendationId,
      payload,
    }: {
      recommendationId: string;
      payload: FeedRecommendationDecisionRequest;
    }) => decideFeedRecommendation(recommendationId, payload),
    onSuccess: async () => invalidateDiscoveryQueries(queryClient),
  });
}

export function useResetFeedRecommendationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recommendationId: string) => resetFeedRecommendation(recommendationId),
    onSuccess: async () => invalidateDiscoveryQueries(queryClient),
  });
}
