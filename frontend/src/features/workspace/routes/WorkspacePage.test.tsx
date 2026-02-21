import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkspaceSearch } from "../../../shared/types/contracts";
import { WorkspacePage } from "./WorkspacePage";

const mediaState = {
  mobile: false,
  tablet: false,
};

const navigateMock = vi.fn();
const markScopeReadMutate = vi.fn();
const patchArticleMutate = vi.fn();

vi.mock("@mui/material", async () => {
  const actual = await vi.importActual<typeof import("@mui/material")>("@mui/material");
  return {
    ...actual,
    useMediaQuery: vi.fn((query: string) => {
      if (query.includes("760")) {
        return mediaState.mobile;
      }
      if (query.includes("1200")) {
        return mediaState.tablet || mediaState.mobile;
      }
      return false;
    }),
  };
});

vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-router")>("@tanstack/react-router");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../../entities/navigation/model", async () => {
  const actual = await vi.importActual<typeof import("../../../entities/navigation/model")>(
    "../../../entities/navigation/model"
  );
  return {
    ...actual,
    getScopeLabel: () => "All articles",
    toNavigationHierarchy: () => ({
      sections: [],
      systems: [
        {
          key: "all",
          title: "All articles",
          unread_count: 3,
          kind: "system",
          scope_type: "system",
          scope_id: "all",
        },
      ],
      folders: [],
      streams: [],
      monitoring_folders: [],
      feeds: [],
    }),
  };
});

vi.mock("../api/workspaceHooks", () => ({
  useNavigationQuery: () => ({ data: { ok: true }, isLoading: false, isError: false }),
  useFoldersQuery: () => ({ data: [], isLoading: false, isError: false }),
  useFeedsQuery: () => ({ data: [], isLoading: false, isError: false }),
  useArticlesQuery: () => ({
    data: {
      items: [
        {
          id: "article-1",
          feed_id: null,
          feed_title: "Feed source",
          title: "First article",
          canonical_url: "https://example.com/article-1",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        },
      ],
      total: 1,
    },
    isLoading: false,
    isError: false,
  }),
  useArticleDetailQuery: (articleId: string) => ({
    data: articleId
      ? {
          id: articleId,
          feed_id: null,
          feed_title: "Feed source",
          source_id: "src",
          canonical_url: "https://example.com/article-1",
          title: "First article",
          content_text: "Body",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }
      : undefined,
    isLoading: false,
    isError: false,
  }),
  usePatchArticleStateMutation: () => ({
    mutate: patchArticleMutate,
    isPending: false,
    isError: false,
  }),
  useMarkScopeAsReadMutation: () => ({ mutate: markScopeReadMutate, isPending: false }),
  useCreateFolderMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCreateFeedMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateFolderMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteFolderMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useAssignFeedFolderMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock("../hooks/useWorkspaceShortcuts", () => ({
  useWorkspaceShortcuts: () => {},
}));

function WorkspaceHarness() {
  const [search, setSearch] = useState<WorkspaceSearch>({
    scope_type: "system",
    scope_id: "",
    state: "all",
    sort: "newest",
    q: "",
    article_id: "",
  });

  return (
    <WorkspacePage
      search={search}
      density="compact"
      navPreset="balanced"
      themeMode="dark"
      setThemeMode={vi.fn()}
      setSearch={(patch) => {
        setSearch((previous) => ({ ...previous, ...patch }));
      }}
    />
  );
}

describe("WorkspacePage", () => {
  beforeEach(() => {
    mediaState.mobile = false;
    mediaState.tablet = false;
    navigateMock.mockReset();
    markScopeReadMutate.mockReset();
    patchArticleMutate.mockReset();
  });

  it("uses desktop 3-pane layout with visible navigation and splitters", () => {
    render(<WorkspaceHarness />);

    expect(document.querySelector('[data-layout-mode="desktop"]')).toBeTruthy();
    expect(screen.getByRole("button", { name: "Feeds" })).toBeVisible();
    expect(screen.getByText("System")).toBeVisible();
    expect(screen.getByRole("separator", { name: "Resize navigation pane" })).toBeVisible();
    expect(screen.getByRole("separator", { name: "Resize reader pane" })).toBeVisible();
  });

  it("uses tablet 2-pane layout with collapsible navigation drawer", () => {
    mediaState.tablet = true;
    render(<WorkspaceHarness />);

    expect(document.querySelector('[data-layout-mode="tablet"]')).toBeTruthy();
    expect(screen.getByRole("button", { name: "Nav" })).toBeVisible();
    expect(screen.queryByText("System")).toBeNull();
    expect(screen.getByRole("heading", { name: "First article" })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Nav" }));
    expect(screen.getByText("System")).toBeVisible();
  });

  it("uses mobile single-pane flow with back-to-list and back-to-nav controls", () => {
    mediaState.mobile = true;
    mediaState.tablet = true;
    render(<WorkspaceHarness />);

    expect(document.querySelector('[data-layout-mode="mobile"]')).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Settings" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Help" })).toBeNull();
    expect(screen.getByRole("button", { name: /Back to nav/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /First article/i })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /First article/i }));

    expect(screen.queryByRole("button", { name: /First article/i })).toBeNull();
    expect(screen.getByRole("button", { name: /Back to list/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /Back to nav/i })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /Back to list/i }));
    expect(screen.getByRole("button", { name: /First article/i })).toBeVisible();
  });
});
