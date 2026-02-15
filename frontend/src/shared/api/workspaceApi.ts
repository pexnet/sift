import {
  parseArticleDetail,
  parseArticleList,
  parsePatchArticleStateRequest,
} from "../../entities/article/model";
import { parseNavigationResponse } from "../../entities/navigation/model";
import type {
  ArticleDetail,
  ArticleListResponse,
  PatchArticleStateRequest,
  WorkspaceSearch,
} from "../types/contracts";
import { apiClient } from "./client";

const NAVIGATION_ENDPOINT = "/api/v1/navigation";
const ARTICLES_ENDPOINT = "/api/v1/articles";

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
