import {
  parseBulkPatchArticleStateRequest,
  parseArticleDetail,
  parseArticleList,
  parsePatchArticleStateRequest,
} from "../../entities/article/model";
import { parseDashboardSummaryResponse } from "../../entities/navigation/dashboard";
import { parsePluginAreasResponse } from "../../entities/navigation/plugins";
import { parseNavigationResponse } from "../../entities/navigation/model";
import type {
  ArticleDetail,
  ArticleListResponse,
  ArticleScopeMarkReadRequest,
  ArticleScopeMarkReadResponse,
  ArticleStateBulkPatchRequest,
  Feed,
  FeedCreateRequest,
  FeedFolder,
  FeedFolderAssignmentRequest,
  FeedFolderCreateRequest,
  FeedFolderUpdateRequest,
  PatchArticleStateRequest,
  DashboardSummary,
  PluginArea,
  WorkspaceSearch,
} from "../types/contracts";
import { apiClient } from "./client";

const NAVIGATION_ENDPOINT = "/api/v1/navigation";
const ARTICLES_ENDPOINT = "/api/v1/articles";
const FOLDERS_ENDPOINT = "/api/v1/folders";
const FEEDS_ENDPOINT = "/api/v1/feeds";
const PLUGIN_AREAS_ENDPOINT = "/api/v1/plugins/areas";
const DASHBOARD_SUMMARY_ENDPOINT = "/api/v1/dashboard/summary";

function toArticleSearchParams(search: WorkspaceSearch): URLSearchParams {
  const params = new URLSearchParams({
    scope_type: search.scope_type,
    state: search.state,
    sort: search.sort,
    limit: "50",
    offset: "0",
  });

  if (search.scope_id) {
    params.set("scope_id", search.scope_id);
  }
  if (search.q) {
    params.set("q", search.q);
  }

  return params;
}

export async function getNavigation() {
  const payload = await apiClient.get<unknown>(NAVIGATION_ENDPOINT);
  return parseNavigationResponse(payload);
}

export async function getPluginAreas(): Promise<PluginArea[]> {
  const payload = await apiClient.get<unknown>(PLUGIN_AREAS_ENDPOINT);
  return parsePluginAreasResponse(payload);
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const payload = await apiClient.get<unknown>(DASHBOARD_SUMMARY_ENDPOINT);
  return parseDashboardSummaryResponse(payload);
}

export async function getArticles(search: WorkspaceSearch): Promise<ArticleListResponse> {
  const payload = await apiClient.get<unknown>(`${ARTICLES_ENDPOINT}?${toArticleSearchParams(search).toString()}`);
  return parseArticleList(payload);
}

export async function getArticleDetail(articleId: string): Promise<ArticleDetail> {
  const payload = await apiClient.get<unknown>(`${ARTICLES_ENDPOINT}/${articleId}`);
  return parseArticleDetail(payload);
}

export async function patchArticleState(articleId: string, payload: PatchArticleStateRequest) {
  const request = parsePatchArticleStateRequest(payload);
  await apiClient.patch<PatchArticleStateRequest, unknown>(`${ARTICLES_ENDPOINT}/${articleId}/state`, request);
}

export async function bulkPatchArticleState(payload: ArticleStateBulkPatchRequest): Promise<number> {
  const request = parseBulkPatchArticleStateRequest(payload);
  const response = await apiClient.post<ArticleStateBulkPatchRequest, { updated_count: number }>(
    `${ARTICLES_ENDPOINT}/state/bulk`,
    request
  );
  return response.updated_count;
}

export async function markScopeAsRead(payload: ArticleScopeMarkReadRequest): Promise<number> {
  const response = await apiClient.post<ArticleScopeMarkReadRequest, ArticleScopeMarkReadResponse>(
    `${ARTICLES_ENDPOINT}/state/mark-scope-read`,
    payload
  );
  return response.updated_count;
}

export async function getFolders(): Promise<FeedFolder[]> {
  return apiClient.get<FeedFolder[]>(FOLDERS_ENDPOINT);
}

export async function createFolder(payload: FeedFolderCreateRequest): Promise<FeedFolder> {
  return apiClient.post<FeedFolderCreateRequest, FeedFolder>(FOLDERS_ENDPOINT, payload);
}

export async function updateFolder(folderId: string, payload: FeedFolderUpdateRequest): Promise<FeedFolder> {
  return apiClient.patch<FeedFolderUpdateRequest, FeedFolder>(`${FOLDERS_ENDPOINT}/${folderId}`, payload);
}

export async function deleteFolder(folderId: string): Promise<void> {
  await apiClient.request<null>(`${FOLDERS_ENDPOINT}/${folderId}`, { method: "DELETE" });
}

export async function getFeeds(): Promise<Feed[]> {
  return apiClient.get<Feed[]>(FEEDS_ENDPOINT);
}

export async function createFeed(payload: FeedCreateRequest): Promise<Feed> {
  return apiClient.post<FeedCreateRequest, Feed>(FEEDS_ENDPOINT, payload);
}

export async function assignFeedFolder(feedId: string, payload: FeedFolderAssignmentRequest): Promise<Feed> {
  return apiClient.patch<FeedFolderAssignmentRequest, Feed>(`${FEEDS_ENDPOINT}/${feedId}/folder`, payload);
}
