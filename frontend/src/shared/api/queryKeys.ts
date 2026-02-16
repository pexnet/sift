import type { WorkspaceSearch } from "../types/contracts";

export const queryKeys = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  navigation: () => ["navigation"] as const,
  streams: () => ["streams"] as const,
  folders: () => ["folders"] as const,
  feeds: () => ["feeds"] as const,
  articles: (search: WorkspaceSearch) =>
    ["articles", search.scope_type, search.scope_id, search.state, search.sort, search.q] as const,
  articleDetail: (articleId: string) => ["article", articleId] as const,
};
