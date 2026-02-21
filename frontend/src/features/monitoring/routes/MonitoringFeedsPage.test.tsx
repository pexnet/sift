import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { ApiError } from "../../../shared/api/client";
import type {
  KeywordStream,
  KeywordStreamCreateRequest,
  StreamBackfillResult,
  KeywordStreamUpdateRequest,
} from "../../../shared/types/contracts";
import {
  useCreateStreamMutation,
  useDeleteStreamMutation,
  useRunStreamBackfillMutation,
  useStreamsQuery,
  useUpdateStreamMutation,
} from "../api/monitoringHooks";
import { MonitoringFeedsPage } from "./MonitoringFeedsPage";

vi.mock("../api/monitoringHooks", () => ({
  useStreamsQuery: vi.fn(),
  useCreateStreamMutation: vi.fn(),
  useUpdateStreamMutation: vi.fn(),
  useDeleteStreamMutation: vi.fn(),
  useRunStreamBackfillMutation: vi.fn(),
}));

const useStreamsQueryMock = vi.mocked(useStreamsQuery);
const useCreateStreamMutationMock = vi.mocked(useCreateStreamMutation);
const useUpdateStreamMutationMock = vi.mocked(useUpdateStreamMutation);
const useDeleteStreamMutationMock = vi.mocked(useDeleteStreamMutation);
const useRunStreamBackfillMutationMock = vi.mocked(useRunStreamBackfillMutation);

function makeStream(overrides: Partial<KeywordStream> = {}): KeywordStream {
  const base: KeywordStream = {
    id: "66ee748f-957b-4c5f-8d6c-5f8fab4dbf2d",
    user_id: "656e7cbf-aa77-4959-af8e-c4e322ae8f3d",
    name: "Threat watch",
    description: "Security monitoring feed",
    folder_id: null,
    is_active: true,
    priority: 100,
    match_query: null,
    include_keywords: ["threat", "alert"],
    exclude_keywords: [],
    include_regex: [],
    exclude_regex: [],
    source_contains: "example.com",
    language_equals: "en",
    classifier_mode: "rules_only",
    classifier_plugin: null,
    classifier_config: {},
    classifier_min_confidence: 0.7,
    created_at: "2026-02-16T10:00:00Z",
    updated_at: "2026-02-16T10:00:00Z",
  };
  return { ...base, ...overrides };
}

function renderPage() {
  return render(
    <AppProviders>
      <MonitoringFeedsPage />
    </AppProviders>
  );
}

describe("MonitoringFeedsPage", () => {
  const createMutateAsync = vi.fn<(payload: KeywordStreamCreateRequest) => Promise<KeywordStream>>();
  const updateMutateAsync = vi.fn<
    (args: { streamId: string; payload: KeywordStreamUpdateRequest }) => Promise<KeywordStream>
  >();
  const deleteMutateAsync = vi.fn<(streamId: string) => Promise<void>>();
  const backfillMutateAsync = vi.fn<(streamId: string) => Promise<StreamBackfillResult>>();

  beforeEach(() => {
    vi.clearAllMocks();
    useStreamsQueryMock.mockReturnValue({
      data: [makeStream()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStreamsQuery>);
    useCreateStreamMutationMock.mockReturnValue({
      mutateAsync: createMutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateStreamMutation>);
    useUpdateStreamMutationMock.mockReturnValue({
      mutateAsync: updateMutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateStreamMutation>);
    useDeleteStreamMutationMock.mockReturnValue({
      mutateAsync: deleteMutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useDeleteStreamMutation>);
    useRunStreamBackfillMutationMock.mockReturnValue({
      mutateAsync: backfillMutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useRunStreamBackfillMutation>);
  });

  it("renders existing monitoring feeds and settings entry links", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Monitoring feeds" })).toBeVisible();
    expect(screen.getByText("Threat watch")).toBeVisible();
    expect(screen.getByRole("button", { name: /Select monitoring feed Threat watch/i })).toBeVisible();
  });

  it("creates a monitoring feed from form input", async () => {
    useStreamsQueryMock.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStreamsQuery>);
    createMutateAsync.mockResolvedValue(makeStream({ name: "corelight" }));

    renderPage();

    fireEvent.change(screen.getByRole("textbox", { name: /Name/i }), {
      target: { value: "corelight feed" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Search query \(v1\)/i }), {
      target: { value: "corelight AND microsoft" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Include keywords/i }), {
      target: { value: "corelight, microsoft" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Show advanced options/i }));
    fireEvent.change(screen.getByRole("textbox", { name: /Include regex/i }), {
      target: { value: "cve-\\d{4}-\\d+" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create monitoring feed" }));

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "corelight feed",
          folder_id: null,
          match_query: "corelight AND microsoft",
          include_keywords: ["corelight", "microsoft"],
          include_regex: ["cve-\\d{4}-\\d+"],
          classifier_mode: "rules_only",
        })
      );
    });
  });

  it("edits an existing monitoring feed", async () => {
    updateMutateAsync.mockResolvedValue(makeStream({ name: "edited stream" }));

    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Select monitoring feed Threat watch/i }));
    fireEvent.change(screen.getByRole("textbox", { name: /Name/i }), {
      target: { value: "edited stream" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => {
      expect(updateMutateAsync).toHaveBeenCalledTimes(1);
    });
    expect(updateMutateAsync.mock.calls[0]?.[0].streamId).toBe("66ee748f-957b-4c5f-8d6c-5f8fab4dbf2d");
    expect(updateMutateAsync.mock.calls[0]?.[0].payload.name).toBe("edited stream");
  });

  it("shows explicit feedback when backfill endpoint is unavailable", async () => {
    backfillMutateAsync.mockRejectedValue(new ApiError("Request failed with status 404", 404));

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /Run backfill for Threat watch/i }));

    await waitFor(() => {
      expect(screen.getByText("Backfill endpoint is not available yet in this build.")).toBeVisible();
    });
  });

  it("shows success feedback when backfill completes", async () => {
    backfillMutateAsync.mockResolvedValue({
      stream_id: "66ee748f-957b-4c5f-8d6c-5f8fab4dbf2d",
      scanned_count: 5,
      previous_match_count: 1,
      matched_count: 2,
    });

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /Run backfill for Threat watch/i }));

    await waitFor(() => {
      expect(screen.getByText("Backfill completed: 2 matched of 5 scanned.")).toBeVisible();
    });
  });

  it("passes classifier config JSON when classifier mode is enabled", async () => {
    createMutateAsync.mockResolvedValue(makeStream({ name: "plugin stream" }));

    renderPage();

    fireEvent.change(screen.getByRole("textbox", { name: /Name/i }), {
      target: { value: "plugin stream" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Show advanced options/i }));
    fireEvent.mouseDown(screen.getByLabelText(/Classifier mode/i));
    fireEvent.click(screen.getByRole("option", { name: "Classifier only" }));
    fireEvent.change(screen.getByRole("textbox", { name: /Classifier plugin/i }), {
      target: { value: "keyword_heuristic_classifier" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Classifier config \(JSON\)/i }), {
      target: { value: '{"require_all_include_keywords":true}' },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create monitoring feed" }));

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          classifier_mode: "classifier_only",
          classifier_plugin: "keyword_heuristic_classifier",
          classifier_config: { require_all_include_keywords: true },
        })
      );
    });
  });
});
