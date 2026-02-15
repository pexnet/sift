import { render } from "@testing-library/react";
import { useRef } from "react";
import { describe, expect, it, vi } from "vitest";

import type { ArticleListItem, WorkspaceSearch } from "../../../shared/types/contracts";
import { useWorkspaceShortcuts } from "./useWorkspaceShortcuts";

const baseSearch: WorkspaceSearch = {
  scope_type: "system",
  scope_id: "",
  state: "all",
  sort: "newest",
  q: "",
  article_id: "",
};

const sampleArticle: ArticleListItem = {
  id: "11111111-1111-1111-1111-111111111111",
  feed_id: null,
  feed_title: "Feed",
  title: "Article",
  canonical_url: null,
  published_at: null,
  created_at: "2026-01-01T00:00:00Z",
  is_read: false,
  is_starred: false,
  is_archived: false,
  stream_ids: [],
};

describe("useWorkspaceShortcuts", () => {
  it("handles keyboard shortcuts", () => {
    const moveSelection = vi.fn();
    const openSelection = vi.fn();
    const toggleRead = vi.fn();
    const toggleSaved = vi.fn();

    function TestHarness() {
      const ref = useRef<HTMLInputElement | null>(null);

      useWorkspaceShortcuts({
        articleItems: [sampleArticle],
        search: baseSearch,
        searchInputRef: ref,
        selectedArticle: sampleArticle,
        moveSelection,
        openSelection,
        toggleRead,
        toggleSaved,
      });

      return <input ref={ref} />;
    }

    render(<TestHarness />);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "j" }));
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k" }));
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "o" }));
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "m" }));
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "s" }));

    expect(moveSelection).toHaveBeenCalledWith(1);
    expect(moveSelection).toHaveBeenCalledWith(-1);
    expect(openSelection).toHaveBeenCalledTimes(1);
    expect(toggleRead).toHaveBeenCalledTimes(1);
    expect(toggleSaved).toHaveBeenCalledTimes(1);
  });
});
