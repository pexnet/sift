import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { NavigationHierarchy } from "../../../entities/navigation/model";
import type { FeedFolder } from "../../../shared/types/contracts";
import { NAV_FOLDERS_EXPANDED_KEY } from "../../../shared/lib/storage";
import { NavigationPane } from "./NavigationPane";

const folders: FeedFolder[] = [];

const hierarchy: NavigationHierarchy = {
  sections: [],
  systems: [
    {
      key: "all",
      title: "All articles",
      unread_count: 5,
      kind: "system",
      scope_type: "system",
      scope_id: "all",
    },
  ],
  folders: [
    {
      id: "ef1ecd29-2f93-49d6-ae70-c989df4da59f",
      name: "Security",
      unread_count: 2,
      kind: "folder",
      scope_type: "folder",
      scope_id: "ef1ecd29-2f93-49d6-ae70-c989df4da59f",
      is_unfiled: false,
      feeds: [
        {
          kind: "feed",
          id: "d60831f4-f2e5-45ef-8b2f-2f29fed2abf5",
          title: "Alpha Feed",
          unread_count: 1,
          folder_id: "ef1ecd29-2f93-49d6-ae70-c989df4da59f",
          folder_name: "Security",
          scope_type: "feed",
          scope_id: "d60831f4-f2e5-45ef-8b2f-2f29fed2abf5",
        },
      ],
    },
    {
      id: "4931b525-21fa-4867-a6e1-4e4b0f780980",
      name: "Tech",
      unread_count: 1,
      kind: "folder",
      scope_type: "folder",
      scope_id: "4931b525-21fa-4867-a6e1-4e4b0f780980",
      is_unfiled: false,
      feeds: [
        {
          kind: "feed",
          id: "df9f1c13-d75a-48ec-9e2c-9f69debd7a0d",
          title: "Bravo Feed",
          unread_count: 1,
          folder_id: "4931b525-21fa-4867-a6e1-4e4b0f780980",
          folder_name: "Tech",
          scope_type: "feed",
          scope_id: "df9f1c13-d75a-48ec-9e2c-9f69debd7a0d",
        },
      ],
    },
  ],
  streams: [],
  feeds: [],
};

function renderPane(overrides: Partial<ComponentProps<typeof NavigationPane>> = {}) {
  const defaults: ComponentProps<typeof NavigationPane> = {
    density: "compact",
    hierarchy,
    folders,
    feedIconByFeedId: {
      "d60831f4-f2e5-45ef-8b2f-2f29fed2abf5": "https://example.com/favicon.ico",
      "df9f1c13-d75a-48ec-9e2c-9f69debd7a0d": "https://example.org/favicon.ico",
    },
    selectedScopeType: "system",
    selectedScopeKey: "all",
    isLoading: false,
    isError: false,
    onSelectSystem: vi.fn(),
    onSelectFolder: vi.fn(),
    onSelectFeed: vi.fn(),
    onSelectStream: vi.fn(),
    onCreateFolder: vi.fn(async () => {}),
    onRenameFolder: vi.fn(async () => {}),
    onDeleteFolder: vi.fn(async () => {}),
    onAssignFeedFolder: vi.fn(async () => {}),
    isFolderMutationPending: false,
    isAssignPending: false,
    onToggleTheme: vi.fn(),
    themeMode: "light",
    onDensityChange: vi.fn(),
  };

  return render(<NavigationPane {...defaults} {...overrides} />);
}

describe("NavigationPane", () => {
  const storage = window.localStorage;

  beforeEach(() => {
    storage.clear();
  });

  it("selects folder on row click without toggling collapse", () => {
    storage.removeItem(NAV_FOLDERS_EXPANDED_KEY);
    const onSelectFolder = vi.fn();
    renderPane({ onSelectFolder });

    fireEvent.click(screen.getByText("Security"));
    expect(onSelectFolder).toHaveBeenCalledWith("ef1ecd29-2f93-49d6-ae70-c989df4da59f");
    expect(screen.getByText("Alpha Feed")).toBeVisible();
  });

  it("toggles folder collapse with one chevron click", async () => {
    storage.removeItem(NAV_FOLDERS_EXPANDED_KEY);
    renderPane();

    fireEvent.click(screen.getByRole("button", { name: /Collapse folder Security/i }));
    await waitFor(() => {
      expect(screen.queryByText("Alpha Feed")).toBeNull();
    });
  });

  it("supports collapse all and expand all controls", async () => {
    storage.removeItem(NAV_FOLDERS_EXPANDED_KEY);
    renderPane();

    fireEvent.click(screen.getByRole("button", { name: /Collapse all/i }));
    await waitFor(() => {
      expect(screen.queryByText("Alpha Feed")).toBeNull();
      expect(screen.queryByText("Bravo Feed")).toBeNull();
    });

    fireEvent.click(screen.getByRole("button", { name: /Expand all/i }));
    await waitFor(() => {
      expect(screen.getByText("Alpha Feed")).toBeVisible();
      expect(screen.getByText("Bravo Feed")).toBeVisible();
    });
  });

  it("falls back to avatar initials when feed icon fails", async () => {
    storage.removeItem(NAV_FOLDERS_EXPANDED_KEY);
    renderPane();

    const image = screen.getByAltText("Alpha Feed");
    fireEvent.error(image);

    await waitFor(() => {
      expect(screen.queryByAltText("Alpha Feed")).toBeNull();
    });
    expect(screen.getByText("A")).toBeVisible();
  });
});
