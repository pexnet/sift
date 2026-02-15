import {
  parseArticleDetail,
  parseArticleList,
  parsePatchArticleStateRequest,
} from "../../entities/article/model";
import { parseNavigationResponse } from "../../entities/navigation/model";
import type {
  ArticleDetail,
  ArticleListResponse,
  Feed,
  FeedFolder,
  FeedFolderAssignmentRequest,
  FeedFolderCreateRequest,
  FeedFolderUpdateRequest,
  PatchArticleStateRequest,
  WorkspaceSearch,
} from "../types/contracts";
import { apiClient } from "./client";

const NAVIGATION_ENDPOINT = "/api/v1/navigation";
const ARTICLES_ENDPOINT = "/api/v1/articles";
const FOLDERS_ENDPOINT = "/api/v1/folders";
const FEEDS_ENDPOINT = "/api/v1/feeds";

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

export async function assignFeedFolder(feedId: string, payload: FeedFolderAssignmentRequest): Promise<Feed> {
  return apiClient.patch<FeedFolderAssignmentRequest, Feed>(`${FEEDS_ENDPOINT}/${feedId}/folder`, payload);
}
