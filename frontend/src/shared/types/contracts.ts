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
