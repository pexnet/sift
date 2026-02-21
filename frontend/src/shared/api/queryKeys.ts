import type { WorkspaceSearch } from "../types/contracts";

export const queryKeys = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  feedHealthRoot: () => ["feed-health"] as const,
  feedHealth: (filters: {
    lifecycle: string;
    q: string;
    stale_only: boolean;
    error_only: boolean;
    all: boolean;
    limit: number;
    offset: number;
  }) =>
    [
      "feed-health",
      filters.lifecycle,
      filters.q,
      filters.stale_only,
      filters.error_only,
      filters.all,
      filters.limit,
      filters.offset,
    ] as const,
  navigation: () => ["navigation"] as const,
  streams: () => ["streams"] as const,
  folders: () => ["folders"] as const,
  feeds: () => ["feeds"] as const,
  articles: (search: WorkspaceSearch) =>
    ["articles", search.scope_type, search.scope_id, search.state, search.sort, search.q] as const,
  articleDetail: (articleId: string) => ["article", articleId] as const,
};
