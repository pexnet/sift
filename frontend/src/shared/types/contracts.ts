import type { components } from "./generated";

export type AuthUser = components["schemas"]["UserOut"];
export type NavigationResponse = components["schemas"]["NavigationTreeOut"];
export type NavigationSystemNode = components["schemas"]["NavigationSystemNodeOut"];
export type NavigationFolderNode = components["schemas"]["NavigationFolderNodeOut"];
export type NavigationStreamNode = components["schemas"]["NavigationStreamNodeOut"];
export type ArticleListResponse = components["schemas"]["ArticleListResponse"];
export type ArticleListItem = components["schemas"]["ArticleListItemOut"];
export type ArticleDetail = components["schemas"]["ArticleDetailOut"];
export type PatchArticleStateRequest = components["schemas"]["ArticleStatePatch"];
export type ArticleStateBulkPatchRequest = components["schemas"]["ArticleStateBulkPatch"];
export type Feed = components["schemas"]["FeedOut"];
export type FeedFolder = components["schemas"]["FeedFolderOut"];
export type FeedFolderCreateRequest = components["schemas"]["FeedFolderCreate"];
export type FeedFolderUpdateRequest = components["schemas"]["FeedFolderUpdate"];
export type FeedFolderAssignmentRequest = components["schemas"]["FeedFolderAssignmentUpdate"];
export type KeywordStream = components["schemas"]["KeywordStreamOut"];
export type KeywordStreamCreateRequest = components["schemas"]["KeywordStreamCreate"];
export type KeywordStreamUpdateRequest = components["schemas"]["KeywordStreamUpdate"];
export type StreamBackfillResult = {
  stream_id: string;
  scanned_count: number;
  previous_match_count: number;
  matched_count: number;
};

export type ArticleScopeType = "system" | "folder" | "feed" | "stream";
export type ArticleStateFilter = "all" | "unread" | "saved" | "archived" | "fresh" | "recent";
export type ArticleSort = "newest" | "oldest" | "unread_first";

export type WorkspaceSearch = {
  scope_type: ArticleScopeType;
  scope_id: string;
  state: ArticleStateFilter;
  sort: ArticleSort;
  q: string;
  article_id: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  password: string;
  display_name: string;
};
