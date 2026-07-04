import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../../shared/api/queryKeys";
import {
  bulkReorderStreams,
  createStream,
  deleteStream,
  getStreamSummary,
  getStreams,
  runStreamBackfill,
  updateStream,
} from "../../../shared/api/streamsApi";
import type {
  KeywordStreamCreateRequest,
  KeywordStreamUpdateRequest,
  StreamBulkReorderRequest,
} from "../../../shared/types/contracts";

export function useStreamsQuery() {
  return useQuery({
    queryKey: queryKeys.streams(),
    queryFn: getStreams,
  });
}

export function useStreamSummaryQuery(streamId: string | null) {
  return useQuery({
    queryKey: queryKeys.streamSummary(streamId ?? ""),
    queryFn: () => getStreamSummary(streamId!),
    enabled: streamId !== null,
  });
}

export function useCreateStreamMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: KeywordStreamCreateRequest) => createStream(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.streams() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
      ]);
    },
  });
}

export function useUpdateStreamMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ streamId, payload }: { streamId: string; payload: KeywordStreamUpdateRequest }) =>
      updateStream(streamId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.streams() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
      ]);
    },
  });
}

export function useDeleteStreamMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (streamId: string) => deleteStream(streamId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.streams() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
      ]);
    },
  });
}

export function useRunStreamBackfillMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (streamId: string) => runStreamBackfill(streamId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.streams() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
      ]);
    },
  });
}

export function useBulkReorderStreamsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: StreamBulkReorderRequest) => bulkReorderStreams(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.streams() });
    },
  });
}
