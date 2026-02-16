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
        streamNameById={{}}
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
        isMarkAllReadPending={false}
        onSearchChange={vi.fn()}
        onStateChange={vi.fn()}
        onArticleSelect={onSelect}
        onMarkAllRead={vi.fn()}
      />
    );

    expect(screen.getByText("Bump v10.22.1")).toBeInTheDocument();
    expect(screen.getByText("★")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Bump v10.22.1/i }));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("greys out read articles in list rows", () => {
    render(
      <ArticlesPane
        density="compact"
        search={{
          scope_type: "system",
          scope_id: "",
          state: "all",
          sort: "newest",
          q: "",
          article_id: "",
        }}
        scopeLabel="All articles"
        streamNameById={{}}
        articleItems={[
          {
            id: "39c60769-d10b-4e37-9a0d-f4da89bcf9b7",
            feed_id: null,
            feed_title: "CyberChef",
            title: "Already read article",
            canonical_url: null,
            published_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            is_read: true,
            is_starred: false,
            is_archived: false,
            stream_ids: [],
          },
        ]}
        selectedArticleId=""
        isLoading={false}
        isError={false}
        searchInputRef={{ current: null }}
        isMarkAllReadPending={false}
        onSearchChange={vi.fn()}
        onStateChange={vi.fn()}
        onArticleSelect={vi.fn()}
        onMarkAllRead={vi.fn()}
      />
    );

    const readRow = screen.getByRole("button", { name: /Already read article/i });
    expect(readRow.className).toContain("workspace-row--read");
  });

  it("exposes state filter control", () => {
    const onStateChange = vi.fn();
    render(
      <ArticlesPane
        density="compact"
        search={{
          scope_type: "system",
          scope_id: "",
          state: "all",
          sort: "newest",
          q: "",
          article_id: "",
        }}
        scopeLabel="All articles"
        streamNameById={{}}
        articleItems={[]}
        selectedArticleId=""
        isLoading={false}
        isError={false}
        searchInputRef={{ current: null }}
        isMarkAllReadPending={false}
        onSearchChange={vi.fn()}
        onStateChange={onStateChange}
        onArticleSelect={vi.fn()}
        onMarkAllRead={vi.fn()}
      />
    );

    expect(screen.getByLabelText("State")).toBeInTheDocument();
    expect(screen.getByText("All")).toBeInTheDocument();
  });

  it("shows monitoring match explainability label when stream ids map to names", () => {
    render(
      <ArticlesPane
        density="compact"
        search={{
          scope_type: "system",
          scope_id: "",
          state: "all",
          sort: "newest",
          q: "",
          article_id: "",
        }}
        scopeLabel="All articles"
        streamNameById={{
          "fd6dd555-1902-4f29-b5ba-3f5a7246e9f1": "darktrace",
        }}
        articleItems={[
          {
            id: "0e0fe5f9-67b7-4f88-8e95-1dbd0ffeb708",
            feed_id: null,
            feed_title: "CyberChef",
            title: "Matched article",
            canonical_url: null,
            published_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            is_read: false,
            is_starred: false,
            is_archived: false,
            stream_ids: ["fd6dd555-1902-4f29-b5ba-3f5a7246e9f1"],
            stream_match_reasons: {
              "fd6dd555-1902-4f29-b5ba-3f5a7246e9f1": "regex: cve-\\d{4}-\\d+",
            },
          },
        ]}
        selectedArticleId=""
        isLoading={false}
        isError={false}
        searchInputRef={{ current: null }}
        isMarkAllReadPending={false}
        onSearchChange={vi.fn()}
        onStateChange={vi.fn()}
        onArticleSelect={vi.fn()}
        onMarkAllRead={vi.fn()}
      />
    );

    expect(screen.getByText("Matched: darktrace")).toBeVisible();
    expect(screen.getByText("Why matched: darktrace: regex: cve-\\d{4}-\\d+")).toBeVisible();
  });

  it("marks unread items as read from list action", () => {
    const onMarkAllRead = vi.fn();
    render(
      <ArticlesPane
        density="compact"
        search={{
          scope_type: "system",
          scope_id: "",
          state: "all",
          sort: "newest",
          q: "",
          article_id: "",
        }}
        scopeLabel="All articles"
        streamNameById={{}}
        articleItems={[
          {
            id: "e75df5eb-a748-42df-bf46-9cdde7cd5f6c",
            feed_id: null,
            feed_title: "CyberChef",
            title: "Unread one",
            canonical_url: null,
            published_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            is_read: false,
            is_starred: false,
            is_archived: false,
            stream_ids: [],
          },
          {
            id: "56d7f9e0-4aef-4748-a62b-dd9f49e43779",
            feed_id: null,
            feed_title: "CyberChef",
            title: "Already read",
            canonical_url: null,
            published_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            is_read: true,
            is_starred: false,
            is_archived: false,
            stream_ids: [],
          },
        ]}
        selectedArticleId=""
        isLoading={false}
        isError={false}
        searchInputRef={{ current: null }}
        isMarkAllReadPending={false}
        onSearchChange={vi.fn()}
        onStateChange={vi.fn()}
        onArticleSelect={vi.fn()}
        onMarkAllRead={onMarkAllRead}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Mark all as read/i }));
    expect(onMarkAllRead).toHaveBeenCalledTimes(1);
    expect(onMarkAllRead).toHaveBeenCalledWith(["e75df5eb-a748-42df-bf46-9cdde7cd5f6c"]);
  });
});
