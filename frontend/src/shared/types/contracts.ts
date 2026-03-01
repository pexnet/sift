import type { components } from "./generated";

export type AuthUser = components["schemas"]["UserOut"];
export type NavigationResponse = components["schemas"]["NavigationTreeOut"];
export type NavigationSystemNode = components["schemas"]["NavigationSystemNodeOut"];
export type NavigationFolderNode = components["schemas"]["NavigationFolderNodeOut"];
export type NavigationStreamNode = components["schemas"]["NavigationStreamNodeOut"];
export type ArticleListResponse = components["schemas"]["ArticleListResponse"];
export type ArticleListItem = components["schemas"]["ArticleListItemOut"];
export type ArticleDetail = Omit<components["schemas"]["ArticleDetailOut"], "fulltext_status" | "content_source"> & {
  fulltext_status?: "idle" | "pending" | "succeeded" | "failed";
  content_source?: "feed_excerpt" | "full_article";
};
export type ArticleFulltextFetchResult = components["schemas"]["ArticleFulltextFetchOut"];
export type PatchArticleStateRequest = components["schemas"]["ArticleStatePatch"];
export type ArticleStateBulkPatchRequest = components["schemas"]["ArticleStateBulkPatch"];
export type Feed = components["schemas"]["FeedOut"];
export type FeedCreateRequest = components["schemas"]["FeedCreate"];
export type FeedSettingsUpdateRequest = components["schemas"]["FeedSettingsUpdate"];
export type FeedLifecycleUpdateRequest = components["schemas"]["FeedLifecycleUpdate"];
export type FeedLifecycleResult = components["schemas"]["FeedLifecycleResultOut"];
export type FeedHealthItem = components["schemas"]["FeedHealthItemOut"];
export type FeedHealthSummary = components["schemas"]["FeedHealthSummaryOut"];
export type FeedHealthListResponse = components["schemas"]["FeedHealthListResponse"];
export type FeedHealthLifecycleFilter = "all" | "active" | "paused" | "archived";
export type FeedHealthQueryParams = {
  lifecycle?: FeedHealthLifecycleFilter;
  q?: string;
  stale_only?: boolean;
  error_only?: boolean;
  all?: boolean;
  limit?: number;
  offset?: number;
};
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
export type PluginArea = {
  id: string;
  title: string;
  icon?: string | null;
  order: number;
  route_key: string;
};
export type DashboardCardAvailabilityStatus = "ready" | "unavailable" | "degraded";
export type DashboardCardAvailability = {
  id: string;
  title: string;
  status: DashboardCardAvailabilityStatus;
  reason?: string | null;
  dependency_spec?: string | null;
};
export type DashboardSummary = {
  cards: DashboardCardAvailability[];
  last_updated_at: string;
};

export type DiscoveryStream = {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  priority: number;
  match_query: string | null;
  include_keywords: string[];
  exclude_keywords: string[];
  created_at: string;
  updated_at: string;
};

export type DiscoveryStreamCreateRequest = {
  name: string;
  description?: string | null;
  is_active?: boolean;
  priority?: number;
  match_query?: string | null;
  include_keywords?: string[];
  exclude_keywords?: string[];
};

export type DiscoveryStreamUpdateRequest = Partial<DiscoveryStreamCreateRequest>;

export type DiscoveryStreamCopyFromMonitoringRequest = {
  monitoring_stream_id: string;
  name?: string | null;
};

export type SearchFeedCandidate = {
  title: string;
  url: string;
  site_url: string | null;
  description: string | null;
  provider: string;
};

export type DiscoveryWarning = {
  code: string;
  provider: string | null;
  message: string;
};

export type DiscoveryGenerateResult = {
  stream_id: string;
  provider_chain: string[];
  query_variants: string[];
  attempted_queries: number;
  candidate_count: number;
  persisted_count: number;
  pending_count: number;
  resolved_existing_count: number;
  candidates: SearchFeedCandidate[];
  warnings: string[];
  warning_details: DiscoveryWarning[];
};

export type FeedRecommendationSource = {
  id: string;
  recommendation_id: string;
  discovery_stream_id: string;
  discovery_stream_name: string | null;
  provider_confidence: number | null;
  evidence: Record<string, unknown> | null;
  created_at: string;
};

export type FeedRecommendation = {
  id: string;
  user_id: string;
  status: "pending" | "accepted" | "denied" | "resolved_existing";
  feed_url: string;
  feed_url_normalized: string;
  feed_title: string | null;
  site_url: string | null;
  confidence: number | null;
  provider: string;
  evidence: Record<string, unknown> | null;
  accepted_feed_id: string | null;
  decided_at: string | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
  sources: FeedRecommendationSource[];
};

export type FeedRecommendationListResponse = {
  items: FeedRecommendation[];
  total: number;
  limit: number;
  offset: number;
};

export type FeedRecommendationDecisionRequest = {
  decision: "accept" | "deny";
};

export type FeedRecommendationSummary = {
  pending_count: number;
  denied_count: number;
  accepted_count: number;
  resolved_existing_count: number;
  total_count: number;
};

export type ArticleScopeType = "system" | "folder" | "feed" | "stream";
export type ArticleStateFilter = "all" | "unread" | "saved" | "archived" | "fresh" | "recent";
export type ArticleSort = "newest" | "oldest" | "unread_first";
export type ArticleScopeMarkReadRequest = {
  scope_type: ArticleScopeType;
  scope_id?: string;
  state: ArticleStateFilter;
  q?: string;
};
export type ArticleScopeMarkReadResponse = {
  updated_count: number;
};

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
