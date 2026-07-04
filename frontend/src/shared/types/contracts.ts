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

export type StreamBulkReorderRequest = {
  reorders: Record<string, number>;
};

export type StreamBulkReorderResponse = {
  updated_count: number;
};

export type StreamSummary = {
  stream_id: string;
  stream_name: string;
  is_active: boolean;
  match_count: number;
  latest_match_at: string | null;
  classifier_run_count: number;
  latest_classifier_run_at: string | null;
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

export type DashboardPriorityProfile = {
  source_weights: Record<string, number>;
  recency_horizon_hours: number;
};

export type DashboardPriorityProfileUpdate = {
  source_weights?: Record<string, number>;
  recency_horizon_hours?: number;
};

export type DashboardPrioritizedArticle = {
  article_id: string;
  title: string;
  feed_title: string | null;
  canonical_url: string | null;
  published_at: string | null;
  priority_score: number;
  score_breakdown: Record<string, number>;
  why_prioritized: string[];
};

export type DashboardPrioritizedQueue = {
  status: string;
  reason: string | null;
  dependency_spec: string | null;
  last_updated_at: string;
  profile: DashboardPriorityProfile;
  items: DashboardPrioritizedArticle[];
};

export type DashboardFeedHealthQueueLag = {
  unavailable_reason?: string | null;
};

export type DashboardFeedHealthCard = {
  status: string;
  reason: string | null;
  dependency_spec: string | null;
  last_updated_at: string;
  stale_feed_count: number;
  error_feed_count: number;
  oldest_success_age_hours: number | null;
  queue_lag: DashboardFeedHealthQueueLag;
};

export type DashboardSavedFollowupItem = {
  article_id: string;
  title: string;
  feed_title: string | null;
  canonical_url: string | null;
  published_at: string | null;
  saved_at: string | null;
};

export type DashboardSavedFollowupCard = {
  status: string;
  reason: string | null;
  dependency_spec: string | null;
  last_updated_at: string;
  saved_count: number;
  latest_items: DashboardSavedFollowupItem[];
};

export type DashboardMonitoringSignalStream = {
  stream_id: string;
  stream_name: string;
  signal_score: number;
  matched_count_window: number;
  unread_count_window: number;
  confidence_summary: { average_confidence: number | null; classifier_run_count: number };
  latest_match_at: string | null;
  score_breakdown: Record<string, number>;
};

export type DashboardMonitoringSignalsCard = {
  status: string;
  reason: string | null;
  dependency_spec: string | null;
  last_updated_at: string;
  window_hours: number;
  streams: DashboardMonitoringSignalStream[];
};

export type DashboardDiscoveryCandidate = {
  article_id: string | null;
  recommendation_id: string | null;
  title: string;
  canonical_url: string | null;
  source_kind: "feed_recommendation" | "monitoring_article";
  candidate_score: number;
  why_candidate: string[];
};

export type DashboardDiscoveryCandidatesCard = {
  status: string;
  reason: string | null;
  dependency_spec: string | null;
  last_updated_at: string;
  pending_recommendation_count: number;
  monitoring_candidate_count: number;
  candidates: DashboardDiscoveryCandidate[];
};

export type DashboardTrendTopic = {
  topic: string;
  momentum_score: number;
  short_window_count: number;
  baseline_count: number;
  source_diversity_count: number;
  representative_article_ids: string[];
};

export type DashboardTrendsCard = {
  status: string;
  reason: string | null;
  dependency_spec: string | null;
  last_updated_at: string;
  window_hours: number;
  baseline_days: number;
  topics: DashboardTrendTopic[];
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
