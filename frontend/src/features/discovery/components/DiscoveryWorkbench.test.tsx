import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RecommendationFilters } from "../../../shared/api/discoveryApi";
import type {
  DiscoveryGenerateResult,
  DiscoveryStream,
  DiscoveryStreamCopyFromMonitoringRequest,
  DiscoveryStreamCreateRequest,
  DiscoveryStreamUpdateRequest,
  FeedRecommendation,
  FeedRecommendationSource,
  FeedRecommendationDecisionRequest,
} from "../../../shared/types/contracts";
import { useStreamsQuery as useMonitoringStreamsQuery } from "../../monitoring/api/monitoringHooks";
import {
  useCopyDiscoveryStreamFromMonitoringMutation,
  useCreateDiscoveryStreamMutation,
  useDecideFeedRecommendationMutation,
  useDeleteDiscoveryStreamMutation,
  useDiscoveryStreamsQuery,
  useFeedRecommendationsQuery,
  useFeedRecommendationSummaryQuery,
  useGenerateDiscoveryStreamMutation,
  useResetFeedRecommendationMutation,
  useUpdateDiscoveryStreamMutation,
} from "../api/discoveryHooks";
import { DiscoveryWorkbench } from "./DiscoveryWorkbench";

vi.mock("../../monitoring/api/monitoringHooks", () => ({
  useStreamsQuery: vi.fn(),
}));

vi.mock("../api/discoveryHooks", () => ({
  useCopyDiscoveryStreamFromMonitoringMutation: vi.fn(),
  useDiscoveryStreamsQuery: vi.fn(),
  useFeedRecommendationSummaryQuery: vi.fn(),
  useCreateDiscoveryStreamMutation: vi.fn(),
  useUpdateDiscoveryStreamMutation: vi.fn(),
  useDeleteDiscoveryStreamMutation: vi.fn(),
  useGenerateDiscoveryStreamMutation: vi.fn(),
  useFeedRecommendationsQuery: vi.fn(),
  useDecideFeedRecommendationMutation: vi.fn(),
  useResetFeedRecommendationMutation: vi.fn(),
}));

const useDiscoveryStreamsQueryMock = vi.mocked(useDiscoveryStreamsQuery);
const useMonitoringStreamsQueryMock = vi.mocked(useMonitoringStreamsQuery);
const useFeedRecommendationSummaryQueryMock = vi.mocked(useFeedRecommendationSummaryQuery);
const useCopyDiscoveryStreamFromMonitoringMutationMock = vi.mocked(useCopyDiscoveryStreamFromMonitoringMutation);
const useCreateDiscoveryStreamMutationMock = vi.mocked(useCreateDiscoveryStreamMutation);
const useUpdateDiscoveryStreamMutationMock = vi.mocked(useUpdateDiscoveryStreamMutation);
const useDeleteDiscoveryStreamMutationMock = vi.mocked(useDeleteDiscoveryStreamMutation);
const useGenerateDiscoveryStreamMutationMock = vi.mocked(useGenerateDiscoveryStreamMutation);
const useFeedRecommendationsQueryMock = vi.mocked(useFeedRecommendationsQuery);
const useDecideFeedRecommendationMutationMock = vi.mocked(useDecideFeedRecommendationMutation);
const useResetFeedRecommendationMutationMock = vi.mocked(useResetFeedRecommendationMutation);

function makeStream(overrides: Partial<DiscoveryStream> = {}): DiscoveryStream {
  return {
    id: "stream-1",
    user_id: "user-1",
    name: "Threat intel",
    description: null,
    is_active: true,
    priority: 100,
    match_query: "threat OR malware",
    include_keywords: ["threat", "malware"],
    exclude_keywords: ["sports"],
    created_at: "2026-03-01T12:00:00Z",
    updated_at: "2026-03-01T12:00:00Z",
    ...overrides,
  };
}

function makeRecommendation(overrides: Partial<FeedRecommendation> = {}): FeedRecommendation {
  return {
    id: "rec-1",
    user_id: "user-1",
    status: "pending",
    feed_url: "https://example.com/feed.xml",
    feed_url_normalized: "https://example.com/feed.xml",
    feed_title: "Example feed",
    site_url: "https://example.com",
    confidence: null,
    provider: "searxng",
    evidence: null,
    accepted_feed_id: null,
    decided_at: null,
    last_seen_at: "2026-03-01T12:00:00Z",
    created_at: "2026-03-01T12:00:00Z",
    updated_at: "2026-03-01T12:00:00Z",
    sources: [],
    ...overrides,
  };
}

function makeRecommendationSource(overrides: Partial<FeedRecommendationSource> = {}): FeedRecommendationSource {
  return {
    id: "source-1",
    recommendation_id: "rec-1",
    discovery_stream_id: "stream-1",
    discovery_stream_name: "Threat watch",
    provider_confidence: null,
    evidence: null,
    created_at: "2026-03-01T12:00:00Z",
    ...overrides,
  };
}

describe("DiscoveryWorkbench", () => {
  const copyFromMonitoringMutateAsync = vi.fn<
    (payload: DiscoveryStreamCopyFromMonitoringRequest) => Promise<DiscoveryStream>
  >();
  const createMutateAsync = vi.fn<(payload: DiscoveryStreamCreateRequest) => Promise<DiscoveryStream>>();
  const updateMutateAsync = vi.fn<
    (args: { streamId: string; payload: DiscoveryStreamUpdateRequest }) => Promise<DiscoveryStream>
  >();
  const deleteMutateAsync = vi.fn<(streamId: string) => Promise<void>>();
  const generateMutateAsync = vi.fn<
    (args: { streamId: string; payload?: { max_results_per_query?: number; max_candidates?: number } }) => Promise<DiscoveryGenerateResult>
  >();
  const decideMutateAsync = vi.fn<
    (args: { recommendationId: string; payload: FeedRecommendationDecisionRequest }) => Promise<FeedRecommendation>
  >();
  const resetMutateAsync = vi.fn<(recommendationId: string) => Promise<FeedRecommendation>>();

  let streamsData: DiscoveryStream[];
  let monitoringStreamsData: Array<{ id: string; name: string }>;
  let recommendationsData: FeedRecommendation[];
  let latestRecommendationFilters: RecommendationFilters | null;

  beforeEach(() => {
    vi.clearAllMocks();

    streamsData = [makeStream()];
    monitoringStreamsData = [{ id: "monitor-1", name: "Threat watch" }];
    recommendationsData = [makeRecommendation()];
    latestRecommendationFilters = null;

    copyFromMonitoringMutateAsync.mockImplementation((payload) => {
      const created = makeStream({
        id: "copied-stream",
        name: payload.name ?? "Threat watch (discovery)",
        match_query: "threat AND intel",
        include_keywords: ["threat", "intel"],
      });
      streamsData = [...streamsData, created];
      return Promise.resolve(created);
    });
    createMutateAsync.mockResolvedValue(makeStream({ id: "stream-created", name: "Created stream" }));
    updateMutateAsync.mockResolvedValue(makeStream({ name: "Updated stream" }));
    deleteMutateAsync.mockResolvedValue(undefined);
    generateMutateAsync.mockResolvedValue({
      stream_id: "stream-1",
      provider_chain: ["searxng"],
      query_variants: ["threat OR malware"],
      attempted_queries: 1,
      candidate_count: 3,
      persisted_count: 3,
      pending_count: 2,
      resolved_existing_count: 1,
      candidates: [],
      warnings: [],
      warning_details: [],
    });
    decideMutateAsync.mockResolvedValue(makeRecommendation({ status: "accepted" }));
    resetMutateAsync.mockResolvedValue(makeRecommendation({ status: "pending" }));

    useDiscoveryStreamsQueryMock.mockImplementation(
      () =>
        ({
          data: streamsData,
          isError: false,
        }) as unknown as ReturnType<typeof useDiscoveryStreamsQuery>
    );
    useMonitoringStreamsQueryMock.mockImplementation(
      () =>
        ({
          data: monitoringStreamsData,
          isError: false,
        }) as unknown as ReturnType<typeof useMonitoringStreamsQuery>
    );
    useFeedRecommendationSummaryQueryMock.mockImplementation(
      () =>
        ({
          data: {
            pending_count: 2,
            denied_count: 1,
            accepted_count: 4,
            resolved_existing_count: 1,
            total_count: 8,
          },
          isError: false,
        }) as unknown as ReturnType<typeof useFeedRecommendationSummaryQuery>
    );
    useCopyDiscoveryStreamFromMonitoringMutationMock.mockImplementation(
      () =>
        ({
          mutateAsync: copyFromMonitoringMutateAsync,
          isPending: false,
        }) as unknown as ReturnType<typeof useCopyDiscoveryStreamFromMonitoringMutation>
    );
    useCreateDiscoveryStreamMutationMock.mockImplementation(
      () =>
        ({
          mutateAsync: createMutateAsync,
          isPending: false,
        }) as unknown as ReturnType<typeof useCreateDiscoveryStreamMutation>
    );
    useUpdateDiscoveryStreamMutationMock.mockImplementation(
      () =>
        ({
          mutateAsync: updateMutateAsync,
          isPending: false,
        }) as unknown as ReturnType<typeof useUpdateDiscoveryStreamMutation>
    );
    useDeleteDiscoveryStreamMutationMock.mockImplementation(
      () =>
        ({
          mutateAsync: deleteMutateAsync,
          isPending: false,
        }) as unknown as ReturnType<typeof useDeleteDiscoveryStreamMutation>
    );
    useGenerateDiscoveryStreamMutationMock.mockImplementation(
      () =>
        ({
          mutateAsync: generateMutateAsync,
          isPending: false,
        }) as unknown as ReturnType<typeof useGenerateDiscoveryStreamMutation>
    );
    useFeedRecommendationsQueryMock.mockImplementation(
      (filters) =>
        ({
          data: {
            items: recommendationsData,
            total: recommendationsData.length,
            limit: 100,
            offset: 0,
          },
          isError: false,
          isLoading: false,
          appliedFilters: (latestRecommendationFilters = filters),
        }) as unknown as ReturnType<typeof useFeedRecommendationsQuery>
    );
    useDecideFeedRecommendationMutationMock.mockImplementation(
      () =>
        ({
          mutateAsync: decideMutateAsync,
          isPending: false,
        }) as unknown as ReturnType<typeof useDecideFeedRecommendationMutation>
    );
    useResetFeedRecommendationMutationMock.mockImplementation(
      () =>
        ({
          mutateAsync: resetMutateAsync,
          isPending: false,
        }) as unknown as ReturnType<typeof useResetFeedRecommendationMutation>
    );
  });

  it("creates a discovery stream from form input", async () => {
    streamsData = [];
    createMutateAsync.mockImplementation((payload) => {
      const created = makeStream({
        id: "stream-created",
        name: payload.name,
        match_query: payload.match_query ?? null,
        include_keywords: payload.include_keywords ?? [],
        exclude_keywords: payload.exclude_keywords ?? [],
      });
      streamsData = [created];
      return Promise.resolve(created);
    });
    render(<DiscoveryWorkbench mode="settings" />);

    fireEvent.change(screen.getByRole("textbox", { name: /^Name$/i }), { target: { value: "My stream" } });
    fireEvent.change(screen.getByRole("textbox", { name: /Include keywords/i }), {
      target: { value: "Alpha, alpha, Beta" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create stream" }));

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith({
        name: "My stream",
        match_query: null,
        include_keywords: ["Alpha", "Beta"],
        exclude_keywords: [],
        is_active: true,
      });
    });
    expect(screen.getByText("Discovery stream created.")).toBeVisible();
  });

  it("copies a monitoring feed into discovery stream", async () => {
    render(<DiscoveryWorkbench mode="settings" />);

    fireEvent.mouseDown(screen.getByLabelText("Monitoring feed"));
    fireEvent.click(screen.getByRole("option", { name: "Threat watch" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Discovery name (optional)" }), {
      target: { value: "Threat discovery" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Copy" }));

    await waitFor(() => {
      expect(copyFromMonitoringMutateAsync).toHaveBeenCalledWith({
        monitoring_stream_id: "monitor-1",
        name: "Threat discovery",
      });
    });
    expect(screen.getByText("Monitoring feed copied into discovery stream.")).toBeVisible();
  });

  it("edits selected stream and runs generation", async () => {
    render(<DiscoveryWorkbench mode="settings" />);

    fireEvent.click(screen.getByRole("button", { name: "Threat intel" }));
    fireEvent.change(screen.getByRole("textbox", { name: /^Name$/i }), { target: { value: "Threat intel updated" } });
    fireEvent.change(screen.getByRole("textbox", { name: /Core query/i }), {
      target: { value: "threat AND intel" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => {
      expect(updateMutateAsync).toHaveBeenCalledWith({
        streamId: "stream-1",
        payload: {
          name: "Threat intel updated",
          match_query: "threat AND intel",
          include_keywords: ["threat", "malware"],
          exclude_keywords: ["sports"],
          is_active: true,
        },
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));
    await waitFor(() => {
      expect(generateMutateAsync).toHaveBeenCalledWith({ streamId: "stream-1" });
    });
    expect(screen.getByText("Generated 3 candidates (2 pending, 1 resolved existing).")).toBeVisible();
  });

  it("supports recommendation accept/deny/reset actions", async () => {
    recommendationsData = [
      makeRecommendation({ id: "rec-pending", status: "pending", feed_title: "Pending feed" }),
      makeRecommendation({ id: "rec-denied", status: "denied", feed_title: "Denied feed" }),
    ];
    render(<DiscoveryWorkbench mode="workspace" />);

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => {
      expect(decideMutateAsync).toHaveBeenCalledWith({
        recommendationId: "rec-pending",
        payload: { decision: "accept" },
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Deny" }));
    await waitFor(() => {
      expect(decideMutateAsync).toHaveBeenCalledWith({
        recommendationId: "rec-pending",
        payload: { decision: "deny" },
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    await waitFor(() => {
      expect(resetMutateAsync).toHaveBeenCalledWith("rec-denied");
    });
  });

  it("renders source chips and evidence details for recommendations", () => {
    recommendationsData = [
      makeRecommendation({
        id: "rec-evidence",
        feed_title: "Evidence feed",
        evidence: {
          description: "Likely RSS endpoint discovered from provider result.",
          query_variants: ["threat intel", "malware feed"],
        },
        sources: [
          makeRecommendationSource({
            id: "source-a",
            recommendation_id: "rec-evidence",
            discovery_stream_id: "stream-a",
            discovery_stream_name: "Threat watch",
            provider_confidence: 0.82,
            evidence: { query_variants: ["threat intel"] },
          }),
          makeRecommendationSource({
            id: "source-b",
            recommendation_id: "rec-evidence",
            discovery_stream_id: "stream-b",
            discovery_stream_name: "Vendors",
            provider_confidence: null,
            evidence: { query_variants: ["malware feed"] },
          }),
        ],
      }),
    ];

    render(<DiscoveryWorkbench mode="workspace" />);

    expect(screen.getByText("Source: Threat watch (0.82)")).toBeVisible();
    expect(screen.getByText("Source: Vendors")).toBeVisible();
    expect(screen.getByText("Likely RSS endpoint discovered from provider result.")).toBeVisible();
    expect(screen.getByText("Query: threat intel")).toBeVisible();
    expect(screen.getByText("Query: malware feed")).toBeVisible();
  });

  it("forwards status and query filters to recommendation query hook", async () => {
    render(<DiscoveryWorkbench mode="settings" />);

    expect(latestRecommendationFilters).toEqual({
      status: "pending",
      q: "",
      sort_by: "updated_at",
      sort_direction: "desc",
      limit: 100,
      offset: 0,
    });

    fireEvent.change(screen.getByPlaceholderText("Search recommendations"), {
      target: { value: "security" },
    });
    await waitFor(() => {
      expect(latestRecommendationFilters?.q).toBe("security");
    });

    fireEvent.mouseDown(screen.getByLabelText("Status"));
    fireEvent.click(screen.getByRole("option", { name: "All" }));
    await waitFor(() => {
      expect(latestRecommendationFilters).toEqual({
        q: "security",
        sort_by: "updated_at",
        sort_direction: "desc",
        limit: 100,
        offset: 0,
      });
    });
  });
});
