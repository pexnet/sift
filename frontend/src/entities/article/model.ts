import { z } from "zod";

import type {
  ArticleDetail,
  ArticleListItem,
  ArticleListResponse,
  ArticleStateBulkPatchRequest,
  PatchArticleStateRequest,
  WorkspaceSearch,
} from "../../shared/types/contracts";
import { WORKSPACE_FILTERS_KEY } from "../../shared/lib/storage";

export const DEFAULT_WORKSPACE_SEARCH: WorkspaceSearch = {
  scope_type: "system",
  scope_id: "",
  state: "all",
  sort: "newest",
  q: "",
  article_id: "",
};

const workspaceSearchSchema = z.object({
  scope_type: z.enum(["system", "folder", "feed", "stream"]).default(DEFAULT_WORKSPACE_SEARCH.scope_type),
  scope_id: z.string().default(""),
  state: z.enum(["all", "unread", "saved", "archived", "fresh", "recent"]).default(DEFAULT_WORKSPACE_SEARCH.state),
  sort: z.enum(["newest", "oldest", "unread_first"]).default(DEFAULT_WORKSPACE_SEARCH.sort),
  q: z.string().default(""),
  article_id: z.string().default(""),
});

const articleListItemSchema = z.object({
  id: z.string().uuid(),
  feed_id: z.string().uuid().nullable(),
  feed_title: z.string().nullable(),
  title: z.string(),
  canonical_url: z.string().nullable(),
  published_at: z.string().nullable(),
  created_at: z.string(),
  is_read: z.boolean(),
  is_starred: z.boolean(),
  is_archived: z.boolean(),
  stream_ids: z.array(z.string().uuid()),
});

const articleListSchema = z.object({
  items: z.array(articleListItemSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

const articleDetailSchema = z.object({
  id: z.string().uuid(),
  feed_id: z.string().uuid().nullable(),
  feed_title: z.string().nullable(),
  source_id: z.string(),
  canonical_url: z.string().nullable(),
  title: z.string(),
  content_text: z.string(),
  language: z.string().nullable(),
  published_at: z.string().nullable(),
  created_at: z.string(),
  is_read: z.boolean(),
  is_starred: z.boolean(),
  is_archived: z.boolean(),
  stream_ids: z.array(z.string().uuid()),
});

const patchArticleStateSchema = z
  .object({
    is_read: z.boolean().nullable().optional(),
    is_starred: z.boolean().nullable().optional(),
    is_archived: z.boolean().nullable().optional(),
  })
  .refine(
    (value) =>
      value.is_read !== undefined || value.is_starred !== undefined || value.is_archived !== undefined,
    {
      message: "At least one field must be set.",
    }
  );

const bulkPatchArticleStateSchema = z
  .object({
    article_ids: z.array(z.string().uuid()).min(1).max(500),
    is_read: z.boolean().nullable().optional(),
    is_starred: z.boolean().nullable().optional(),
    is_archived: z.boolean().nullable().optional(),
  })
  .refine(
    (value) =>
      value.is_read !== undefined || value.is_starred !== undefined || value.is_archived !== undefined,
    {
      message: "At least one field must be set.",
    }
  );

export function parseWorkspaceSearch(value: unknown): WorkspaceSearch {
  return workspaceSearchSchema.parse(value) as WorkspaceSearch;
}

export function loadPersistedWorkspaceSearch(): WorkspaceSearch {
  if (typeof window === "undefined") {
    return DEFAULT_WORKSPACE_SEARCH;
  }
  const raw = window.localStorage.getItem(WORKSPACE_FILTERS_KEY);
  if (!raw) {
    return DEFAULT_WORKSPACE_SEARCH;
  }
  try {
    const parsed = parseWorkspaceSearch(JSON.parse(raw));
    return {
      ...parsed,
      article_id: "",
    };
  } catch {
    return DEFAULT_WORKSPACE_SEARCH;
  }
}

export function savePersistedWorkspaceSearch(search: WorkspaceSearch): void {
  if (typeof window === "undefined") {
    return;
  }
  const normalized = parseWorkspaceSearch({
    ...search,
    article_id: "",
  });
  window.localStorage.setItem(WORKSPACE_FILTERS_KEY, JSON.stringify(normalized));
}

export function parseArticleList(payload: unknown): ArticleListResponse {
  return articleListSchema.parse(payload) as ArticleListResponse;
}

export function parseArticleDetail(payload: unknown): ArticleDetail {
  return articleDetailSchema.parse(payload) as ArticleDetail;
}

export function parsePatchArticleStateRequest(payload: PatchArticleStateRequest): PatchArticleStateRequest {
  const parsed = patchArticleStateSchema.parse(payload);
  const normalized: PatchArticleStateRequest = {};

  if (parsed.is_read !== undefined) {
    normalized.is_read = parsed.is_read;
  }
  if (parsed.is_starred !== undefined) {
    normalized.is_starred = parsed.is_starred;
  }
  if (parsed.is_archived !== undefined) {
    normalized.is_archived = parsed.is_archived;
  }

  return normalized;
}

export function parseBulkPatchArticleStateRequest(
  payload: ArticleStateBulkPatchRequest
): ArticleStateBulkPatchRequest {
  const parsed = bulkPatchArticleStateSchema.parse(payload);
  const normalized: ArticleStateBulkPatchRequest = {
    article_ids: parsed.article_ids,
  };

  if (parsed.is_read !== undefined) {
    normalized.is_read = parsed.is_read;
  }
  if (parsed.is_starred !== undefined) {
    normalized.is_starred = parsed.is_starred;
  }
  if (parsed.is_archived !== undefined) {
    normalized.is_archived = parsed.is_archived;
  }

  return normalized;
}

export function findArticleById(items: ArticleListItem[], articleId: string): ArticleListItem | undefined {
  return items.find((item) => item.id === articleId);
}

export function getSelectedArticleId(items: ArticleListItem[], articleId: string): string {
  if (articleId && items.some((item) => item.id === articleId)) {
    return articleId;
  }
  return items[0]?.id ?? "";
}
