import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ArticlesPane } from "./ArticlesPane";

describe("ArticlesPane", () => {
  it("renders compact rows with unread and saved indicators", () => {
    const onSelect = vi.fn();

    render(
      <ArticlesPane
        density="compact"
        search={{
          scope_type: "system",
          scope_id: "",
          state: "unread",
          sort: "newest",
          q: "",
          article_id: "",
        }}
        scopeLabel="All articles"
        articleItems={[
          {
            id: "e75df5eb-a748-42df-bf46-9cdde7cd5f6c",
            feed_id: null,
            feed_title: "CyberChef",
            title: "Bump v10.22.1",
            canonical_url: null,
            published_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            is_read: false,
            is_starred: true,
            is_archived: false,
            stream_ids: [],
          },
        ]}
        selectedArticleId=""
        isLoading={false}
        isError={false}
        searchInputRef={{ current: null }}
        onSearchChange={vi.fn()}
        onStateChange={vi.fn()}
        onArticleSelect={onSelect}
      />
    );

    expect(screen.getByText("Bump v10.22.1")).toBeInTheDocument();
    expect(screen.getByText("★")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Bump v10.22.1/i }));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});
