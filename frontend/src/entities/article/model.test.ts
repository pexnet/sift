import { describe, expect, it } from "vitest";

import { WORKSPACE_FILTERS_KEY } from "../../shared/lib/storage";
import {
  getSelectedArticleId,
  loadPersistedWorkspaceSearch,
  savePersistedWorkspaceSearch,
} from "./model";

const items = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    feed_id: null,
    feed_title: "Feed A",
    title: "Article A",
    canonical_url: null,
    published_at: null,
    created_at: new Date().toISOString(),
    is_read: false,
    is_starred: false,
    is_archived: false,
    stream_ids: [],
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    feed_id: null,
    feed_title: "Feed B",
    title: "Article B",
    canonical_url: null,
    published_at: null,
    created_at: new Date().toISOString(),
    is_read: false,
    is_starred: false,
    is_archived: false,
    stream_ids: [],
  },
];

describe("getSelectedArticleId", () => {
  it("keeps selected id when it exists in current items", () => {
    expect(getSelectedArticleId(items, "22222222-2222-2222-2222-222222222222")).toBe(
      "22222222-2222-2222-2222-222222222222"
    );
  });

  it("falls back to first item when selected id no longer exists", () => {
    expect(getSelectedArticleId(items, "33333333-3333-3333-3333-333333333333")).toBe(
      "11111111-1111-1111-1111-111111111111"
    );
  });

  it("returns empty string for empty list", () => {
    expect(getSelectedArticleId([], "33333333-3333-3333-3333-333333333333")).toBe("");
  });
});

describe("workspace search persistence", () => {
  it("loads default workspace search when no persisted value exists", () => {
    window.localStorage.removeItem(WORKSPACE_FILTERS_KEY);
    const search = loadPersistedWorkspaceSearch();
    expect(search.state).toBe("all");
    expect(search.q).toBe("");
    expect(search.article_id).toBe("");
  });

  it("saves and restores persisted filters without restoring article selection", () => {
    savePersistedWorkspaceSearch({
      scope_type: "system",
      scope_id: "",
      state: "unread",
      sort: "newest",
      q: "corelight",
      article_id: "ignored-article-id",
    });

    const restored = loadPersistedWorkspaceSearch();
    expect(restored.scope_type).toBe("system");
    expect(restored.state).toBe("unread");
    expect(restored.q).toBe("corelight");
    expect(restored.article_id).toBe("");
  });
});
