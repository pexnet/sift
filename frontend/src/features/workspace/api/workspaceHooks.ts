import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getArticleDetail, getArticles, getNavigation, patchArticleState } from "../../../shared/api/workspaceApi";
import { queryKeys } from "../../../shared/api/queryKeys";
import type { PatchArticleStateRequest, WorkspaceSearch } from "../../../shared/types/contracts";

export function useNavigationQuery() {
  return useQuery({
    queryKey: queryKeys.navigation(),
    queryFn: getNavigation,
  });
}

export function useArticlesQuery(search: WorkspaceSearch) {
  return useQuery({
    queryKey: queryKeys.articles(search),
    queryFn: () => getArticles(search),
  });
}

export function useArticleDetailQuery(articleId: string) {
  return useQuery({
    queryKey: queryKeys.articleDetail(articleId),
    queryFn: () => getArticleDetail(articleId),
    enabled: articleId.length > 0,
  });
}

export function usePatchArticleStateMutation(articleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PatchArticleStateRequest) => patchArticleState(articleId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.navigation() }),
        queryClient.invalidateQueries({ queryKey: ["articles"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.articleDetail(articleId) }),
      ]);
    },
  });
}
