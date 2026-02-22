import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../../shared/api/queryKeys";
import {
  assignFeedFolder,
  bulkPatchArticleState,
  createFeed,
  createFolder,
  deleteFolder,
  fetchArticleFulltext,
  getArticleDetail,
  getArticles,
  getFeeds,
  getFolders,
  getNavigation,
  getDashboardSummary,
  getPluginAreas,
  markScopeAsRead,
  patchArticleState,
  updateFolder,
} from "../../../shared/api/workspaceApi";
import type {
  ArticleScopeMarkReadRequest,
  ArticleStateBulkPatchRequest,
  ArticleListResponse,
  FeedFolderAssignmentRequest,
  FeedCreateRequest,
  FeedFolderCreateRequest,
  FeedFolderUpdateRequest,
  PatchArticleStateRequest,
  WorkspaceSearch,
} from "../../../shared/types/contracts";

export function useNavigationQuery() {
  return useQuery({
    queryKey: queryKeys.navigation(),
    queryFn: getNavigation,
  });
}

export function usePluginAreasQuery() {
  return useQuery({
    queryKey: queryKeys.pluginAreas(),
    queryFn: getPluginAreas,
  });
}

export function useDashboardSummaryQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardSummary(),
    queryFn: getDashboardSummary,
    enabled,
  });
}

export function useFoldersQuery() {
  return useQuery({
    queryKey: queryKeys.folders(),
    queryFn: getFolders,
  });
}

export function useFeedsQuery() {
  return useQuery({
    queryKey: queryKeys.feeds(),
    queryFn: getFeeds,
  });
}

export function useArticlesQuery(search: WorkspaceSearch, enabled = true) {
  return useQuery({
    queryKey: queryKeys.articles(search),
    queryFn: () => getArticles(search),
    enabled,
  });
}

export function useArticleDetailQuery(articleId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.articleDetail(articleId),
    queryFn: () => getArticleDetail(articleId),
    enabled: enabled && articleId.length > 0,
  });
}

export function useFetchArticleFulltextMutation(articleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => fetchArticleFulltext(articleId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.articleDetail(articleId) });
    },
  });
}

export function usePatchArticleStateMutation(articleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PatchArticleStateRequest) => patchArticleState(articleId, payload),
    onMutate: async (payload) => {
      await Promise.all([
        queryClient.cancelQueries({ queryKey: ["articles"] }),
        queryClient.cancelQueries({ queryKey: queryKeys.articleDetail(articleId) }),
      ]);

      const previousArticles = queryClient.getQueriesData<ArticleListResponse>({ queryKey: ["articles"] });
      const previousDetail = queryClient.getQueryData(queryKeys.articleDetail(articleId));

      queryClient.setQueriesData<ArticleListResponse>({ queryKey: ["articles"] }, (current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          items: current.items.map((item) => {
            if (item.id !== articleId) {
              return item;
            }
            return {
              ...item,
              is_read: payload.is_read ?? item.is_read,
              is_starred: payload.is_starred ?? item.is_starred,
              is_archived: payload.is_archived ?? item.is_archived,
            };
          }),
        };
      });

      queryClient.setQueryData(queryKeys.articleDetail(articleId), (current: Record<string, unknown> | undefined) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          is_read: payload.is_read ?? current.is_read,
          is_starred: payload.is_starred ?? current.is_starred,
          is_archived: payload.is_archived ?? current.is_archived,
        };
      });

      return { previousArticles, previousDetail };
    },
    onError: (_error, _payload, context) => {
      context?.previousArticles.forEach(([key, value]) => {
        queryClient.setQueryData(key, value);
      });
      queryClient.setQueryData(queryKeys.articleDetail(articleId), context?.previousDetail);
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.articleDetail(articleId) }),
      ]);
    },
  });
}

export function useBulkPatchArticleStateMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ArticleStateBulkPatchRequest) => bulkPatchArticleState(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
        queryClient.invalidateQueries({ queryKey: ["article"] }),
      ]);
    },
  });
}

export function useMarkScopeAsReadMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ArticleScopeMarkReadRequest) => markScopeAsRead(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
        queryClient.invalidateQueries({ queryKey: ["article"] }),
      ]);
    },
  });
}

export function useCreateFolderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FeedFolderCreateRequest) => createFolder(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.folders() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
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
        queryClient.invalidateQueries({ queryKey: queryKeys.feeds() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
      ]);
    },
  });
}

export function useUpdateFolderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ folderId, payload }: { folderId: string; payload: FeedFolderUpdateRequest }) =>
      updateFolder(folderId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.folders() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
      ]);
    },
  });
}

export function useDeleteFolderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (folderId: string) => deleteFolder(folderId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.folders() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.feeds() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
      ]);
    },
  });
}

export function useAssignFeedFolderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ feedId, payload }: { feedId: string; payload: FeedFolderAssignmentRequest }) =>
      assignFeedFolder(feedId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.feeds() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
      ]);
    },
  });
}
