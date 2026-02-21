import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  streams: [
    {
      id: "a951f7ec-1cf6-4e6a-bcb7-26642ab53412",
      name: "[Global] darktrace",
      folder_id: "ef1ecd29-2f93-49d6-ae70-c989df4da59f",
      unread_count: 9,
      kind: "stream",
      scope_type: "stream",
      scope_id: "a951f7ec-1cf6-4e6a-bcb7-26642ab53412",
    },
  ],
  monitoring_folders: [
    {
      id: "ef1ecd29-2f93-49d6-ae70-c989df4da59f",
      name: "Security",
      is_unfiled: false,
      unread_count: 9,
      streams: [
        {
          id: "a951f7ec-1cf6-4e6a-bcb7-26642ab53412",
          name: "[Global] darktrace",
          folder_id: "ef1ecd29-2f93-49d6-ae70-c989df4da59f",
          unread_count: 9,
          kind: "stream",
          scope_type: "stream",
          scope_id: "a951f7ec-1cf6-4e6a-bcb7-26642ab53412",
        },
      ],
    },
    {
      id: null,
      name: "Unfiled",
      is_unfiled: true,
      unread_count: 0,
      streams: [],
    },
  ],
  feeds: [],
};

function renderPane(overrides: Partial<ComponentProps<typeof NavigationPane>> = {}) {
  const defaults: ComponentProps<typeof NavigationPane> = {
    density: "compact",
    navPreset: "balanced",
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
    onCreateFeed: vi.fn(async () => {}),
    onRenameFolder: vi.fn(async () => {}),
    onDeleteFolder: vi.fn(async () => {}),
    onAssignFeedFolder: vi.fn(async () => {}),
    isFolderMutationPending: false,
    isFeedMutationPending: false,
    isAssignPending: false,
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

    expect(screen.getByRole("button", { name: "Add feed" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Add folder" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Folder Security" }));
    expect(onSelectFolder).toHaveBeenCalledWith("ef1ecd29-2f93-49d6-ae70-c989df4da59f");
    expect(screen.getByText("Alpha Feed")).toBeVisible();
  });

  it("creates feed from toolbar add feed dialog", async () => {
    const onCreateFeed = vi.fn(async () => {});
    renderPane({ onCreateFeed });

    fireEvent.click(screen.getByRole("button", { name: "Add feed" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByRole("textbox", { name: /Feed URL/i }), {
      target: { value: "https://example.com/rss.xml" },
    });
    fireEvent.change(within(dialog).getByRole("textbox", { name: /Title \(optional\)/i }), {
      target: { value: "Example Feed" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add feed" }));

    await waitFor(() => {
      expect(onCreateFeed).toHaveBeenCalledWith({
        title: "Example Feed",
        url: "https://example.com/rss.xml",
        folderId: null,
      });
    });
  });

  it("toggles folder collapse with one chevron click", async () => {
    storage.removeItem(NAV_FOLDERS_EXPANDED_KEY);
    renderPane();

    fireEvent.click(screen.getByRole("button", { name: /Collapse folder Security/i }));
    await waitFor(() => {
      expect(screen.queryByText("Alpha Feed")).toBeNull();
    });
  });

  it("supports single-toggle collapse and expand all controls", async () => {
    storage.removeItem(NAV_FOLDERS_EXPANDED_KEY);
    renderPane();

    fireEvent.click(screen.getByRole("button", { name: /Collapse all folders/i }));
    await waitFor(() => {
      expect(screen.queryByText("Alpha Feed")).toBeNull();
      expect(screen.queryByText("Bravo Feed")).toBeNull();
    });

    fireEvent.click(screen.getByRole("button", { name: /Expand all folders/i }));
    await waitFor(() => {
      expect(screen.getByText("Alpha Feed")).toBeVisible();
      expect(screen.getByText("Bravo Feed")).toBeVisible();
    });
  });

  it("renders monitoring section above folders and selects stream scope", () => {
    const onSelectStream = vi.fn();
    renderPane({ onSelectStream });

    const sectionTitles = screen.getAllByText(/Monitoring feeds|Folders/i).map((node) => node.textContent);
    expect(sectionTitles).toEqual(["Monitoring feeds", "Folders"]);

    fireEvent.click(screen.getByRole("button", { name: /\[Global\] darktrace/i }));
    expect(onSelectStream).toHaveBeenCalledWith("a951f7ec-1cf6-4e6a-bcb7-26642ab53412");
  });

  it("collapses and expands monitoring section", async () => {
    renderPane();
    expect(screen.getByText("[Global] darktrace")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /Collapse monitoring feeds/i }));
    await waitFor(() => {
      expect(screen.queryByText("[Global] darktrace")).toBeNull();
    });

    fireEvent.click(screen.getByRole("button", { name: /Expand monitoring feeds/i }));
    await waitFor(() => {
      expect(screen.getByText("[Global] darktrace")).toBeVisible();
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

  it("uses compact feed icon sizing by default", () => {
    renderPane();
    const avatar = document.querySelector(".workspace-nav__feed-avatar");
    expect(avatar).toBeTruthy();
    expect(avatar).toHaveStyle({ width: "14px", height: "14px" });
  });

  it("applies nav visual preset from props", () => {
    const { container, rerender } = renderPane({ navPreset: "balanced" });
    const navRoot = container.querySelector(".workspace-nav");
    expect(navRoot?.className).toContain("workspace-nav--preset-balanced");

    rerender(
      <NavigationPane
        density="compact"
        navPreset="tight"
        hierarchy={hierarchy}
        folders={folders}
        feedIconByFeedId={{
          "d60831f4-f2e5-45ef-8b2f-2f29fed2abf5": "https://example.com/favicon.ico",
          "df9f1c13-d75a-48ec-9e2c-9f69debd7a0d": "https://example.org/favicon.ico",
        }}
        selectedScopeType="system"
        selectedScopeKey="all"
        isLoading={false}
        isError={false}
        onSelectSystem={vi.fn()}
        onSelectFolder={vi.fn()}
        onSelectFeed={vi.fn()}
        onSelectStream={vi.fn()}
        onCreateFolder={vi.fn(async () => {})}
        onCreateFeed={vi.fn(async () => {})}
        onRenameFolder={vi.fn(async () => {})}
        onDeleteFolder={vi.fn(async () => {})}
        onAssignFeedFolder={vi.fn(async () => {})}
        isFolderMutationPending={false}
        isFeedMutationPending={false}
        isAssignPending={false}
      />
    );

    expect(navRoot?.className).toContain("workspace-nav--preset-tight");
  });
});
