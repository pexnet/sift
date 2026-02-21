import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createFeed, getFeedHealth, updateFeedLifecycle, updateFeedSettings } from "../../../shared/api/feedHealthApi";
import { queryKeys } from "../../../shared/api/queryKeys";
import type {
  FeedCreateRequest,
  FeedHealthLifecycleFilter,
  FeedHealthQueryParams,
  FeedLifecycleUpdateRequest,
  FeedSettingsUpdateRequest,
} from "../../../shared/types/contracts";

const DEFAULT_LIMIT = 50;
const DEFAULT_OFFSET = 0;

type FeedHealthFilters = {
  lifecycle: FeedHealthLifecycleFilter;
  q: string;
  stale_only: boolean;
  error_only: boolean;
  all?: boolean;
  limit?: number;
  offset?: number;
};

function normalizeFilters(filters: FeedHealthFilters): Required<FeedHealthQueryParams> & { lifecycle: FeedHealthLifecycleFilter } {
  return {
    lifecycle: filters.lifecycle,
    q: filters.q,
    stale_only: filters.stale_only,
    error_only: filters.error_only,
    all: filters.all ?? false,
    limit: filters.limit ?? DEFAULT_LIMIT,
    offset: filters.offset ?? DEFAULT_OFFSET,
  };
}

export function useFeedHealthQuery(filters: FeedHealthFilters) {
  const normalized = normalizeFilters(filters);
  return useQuery({
    queryKey: queryKeys.feedHealth({
      lifecycle: normalized.lifecycle,
      q: normalized.q,
      stale_only: normalized.stale_only,
      error_only: normalized.error_only,
      all: normalized.all,
      limit: normalized.limit,
      offset: normalized.offset,
    }),
    queryFn: () => getFeedHealth(normalized),
  });
}

export function useUpdateFeedSettingsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ feedId, payload }: { feedId: string; payload: FeedSettingsUpdateRequest }) =>
      updateFeedSettings(feedId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.feedHealthRoot() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.feeds() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
      ]);
    },
  });
}

export function useUpdateFeedLifecycleMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ feedId, payload }: { feedId: string; payload: FeedLifecycleUpdateRequest }) =>
      updateFeedLifecycle(feedId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.feedHealthRoot() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.feeds() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
      ]);
    },
  });
}

export function useCreateFeedMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FeedCreateRequest) => createFeed(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.feedHealthRoot() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.feeds() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
      ]);
    },
  });
}
