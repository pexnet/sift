import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import {
  useFeedHealthQuery,
  useUpdateFeedLifecycleMutation,
  useUpdateFeedSettingsMutation,
} from "../api/feedHealthHooks";
import { FeedHealthPage } from "./FeedHealthPage";

vi.mock("../api/feedHealthHooks", () => ({
  useFeedHealthQuery: vi.fn(),
  useUpdateFeedSettingsMutation: vi.fn(),
  useUpdateFeedLifecycleMutation: vi.fn(),
}));

const useFeedHealthQueryMock = vi.mocked(useFeedHealthQuery);
const useUpdateFeedSettingsMutationMock = vi.mocked(useUpdateFeedSettingsMutation);
const useUpdateFeedLifecycleMutationMock = vi.mocked(useUpdateFeedLifecycleMutation);

const settingsMutateAsync = vi.fn();
const lifecycleMutateAsync = vi.fn();

function renderPage() {
  return render(
    <AppProviders>
      <FeedHealthPage />
    </AppProviders>
  );
}

describe("FeedHealthPage", () => {
  beforeEach(() => {
    useFeedHealthQueryMock.mockClear();
    settingsMutateAsync.mockReset();
    lifecycleMutateAsync.mockReset();
    settingsMutateAsync.mockResolvedValue({
      id: "feed-1",
      title: "Threat feed",
    });
    lifecycleMutateAsync.mockResolvedValue({
      feed: { id: "feed-1" },
      marked_read_count: 2,
    });

    useFeedHealthQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        total: 1,
        limit: 50,
        offset: 0,
        last_updated_at: "2026-02-19T12:00:00Z",
        summary: {
          total_feed_count: 2,
          active_feed_count: 1,
          paused_feed_count: 0,
          archived_feed_count: 1,
          stale_feed_count: 1,
          error_feed_count: 1,
        },
        items: [
          {
            feed_id: "feed-1",
            title: "Threat feed",
            url: "https://example.com/threat.xml",
            site_url: null,
            folder_id: null,
            lifecycle_status: "active",
            fetch_interval_minutes: 30,
            last_fetched_at: "2026-02-19T10:00:00Z",
            last_fetch_success_at: "2026-02-19T10:00:00Z",
            last_fetch_error: "temporary error",
            last_fetch_error_at: "2026-02-19T09:00:00Z",
            is_stale: true,
            stale_age_hours: 8,
            articles_last_7d: 14,
            estimated_articles_per_day_7d: 2,
            unread_count: 4,
          },
        ],
      },
    } as ReturnType<typeof useFeedHealthQuery>);

    useUpdateFeedSettingsMutationMock.mockReturnValue({
      isPending: false,
      mutateAsync: settingsMutateAsync,
    } as unknown as ReturnType<typeof useUpdateFeedSettingsMutation>);

    useUpdateFeedLifecycleMutationMock.mockReturnValue({
      isPending: false,
      mutateAsync: lifecycleMutateAsync,
    } as unknown as ReturnType<typeof useUpdateFeedLifecycleMutation>);
  });

  it("renders feed health data and settings links", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Feed health" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to settings" })).toHaveAttribute("href", "/account");
    expect(screen.getByText(/^Last refreshed:/)).toBeVisible();
    expect(screen.getByText("Filters")).toBeVisible();
    expect(screen.getByText("Threat feed")).toBeVisible();
    expect(screen.getByText("https://example.com/threat.xml")).toBeVisible();
    expect(screen.getByText("Interval: 30m")).toBeVisible();
    expect(screen.getByText("Unread: 4")).toBeVisible();
    expect(screen.getByText("Articles (7d): 14")).toBeVisible();
    expect(screen.getByText("Cadence: 2.00/day")).toBeVisible();
    expect(screen.getByText("Total 2")).toBeVisible();
    expect(screen.getByText("Errors 1")).toBeVisible();
  });

  it("updates feed interval from row control", async () => {
    renderPage();

    const intervalInput = screen.getByLabelText("Fetch interval (minutes)");
    fireEvent.change(intervalInput, { target: { value: "120" } });
    fireEvent.click(screen.getByRole("button", { name: "Save interval" }));

    await waitFor(() => {
      expect(settingsMutateAsync).toHaveBeenCalledWith({
        feedId: "feed-1",
        payload: { fetch_interval_minutes: 120 },
      });
    });
    expect(screen.getByText("Feed settings updated.")).toBeVisible();
  });

  it("archives feed with confirmation and shows marked-read count", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Archive feed" }));

    await waitFor(() => {
      expect(lifecycleMutateAsync).toHaveBeenCalledWith({
        feedId: "feed-1",
        payload: { action: "archive" },
      });
    });
    expect(screen.getByText("Feed archived. Marked 2 unread article(s) as read.")).toBeVisible();
    confirmSpy.mockRestore();
  });

  it("applies and resets filters", async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("Title or URL"), { target: { value: "threat" } });
    fireEvent.click(screen.getByRole("switch", { name: "Stale only" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => {
      expect(useFeedHealthQueryMock).toHaveBeenLastCalledWith({
        lifecycle: "all",
        q: "threat",
        stale_only: true,
        error_only: false,
        limit: 50,
        offset: 0,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    await waitFor(() => {
      expect(useFeedHealthQueryMock).toHaveBeenLastCalledWith({
        lifecycle: "all",
        q: "",
        stale_only: false,
        error_only: false,
        limit: 50,
        offset: 0,
      });
    });
  });
});
