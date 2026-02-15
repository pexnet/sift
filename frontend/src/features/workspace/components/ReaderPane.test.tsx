import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReaderPane } from "./ReaderPane";

describe("ReaderPane", () => {
  it("wires core reader actions", () => {
    const onToggleRead = vi.fn();
    const onToggleSaved = vi.fn();
    const onOpenOriginal = vi.fn();
    const onMoveSelection = vi.fn();

    render(
      <ReaderPane
        selectedArticle={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          title: "Reader title",
          canonical_url: "https://example.com/article",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Body",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={onToggleRead}
        onToggleSaved={onToggleSaved}
        onOpenOriginal={onOpenOriginal}
        onMoveSelection={onMoveSelection}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Mark read/i }));
    fireEvent.click(screen.getByRole("button", { name: /Save/i }));
    fireEvent.click(screen.getByRole("button", { name: /Open original/i }));
    fireEvent.click(screen.getByRole("button", { name: /Prev/i }));
    fireEvent.click(screen.getByRole("button", { name: /Next/i }));

    expect(onToggleRead).toHaveBeenCalledTimes(1);
    expect(onToggleSaved).toHaveBeenCalledTimes(1);
    expect(onOpenOriginal).toHaveBeenCalledTimes(1);
    expect(onMoveSelection).toHaveBeenNthCalledWith(1, -1);
    expect(onMoveSelection).toHaveBeenNthCalledWith(2, 1);
  });

  it("renders back-to-list action when provided", () => {
    const onBackToList = vi.fn();

    render(
      <ReaderPane
        selectedArticle={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          title: "Reader title",
          canonical_url: "https://example.com/article",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Body",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
        onBackToList={onBackToList}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Back to list/i }));
    expect(onBackToList).toHaveBeenCalledTimes(1);
  });
});
