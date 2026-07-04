import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../api/dashboardHooks", () => ({
  useDashboardPrioritizedQueueQuery: () => ({
    data: {
      status: "ready",
      reason: null,
      dependency_spec: null,
      last_updated_at: new Date().toISOString(),
      profile: { source_weights: { feed: 40, monitoring_stream: 60 }, recency_horizon_hours: 24 },
      items: [
        {
          article_id: "a1",
          title: "Priority article",
          feed_title: "Test Feed",
          canonical_url: "https://example.com/a1",
          published_at: new Date().toISOString(),
          priority_score: 80,
          score_breakdown: { feed: 20, monitoring_signal_bonus: 60 },
          why_prioritized: ["Matched monitoring stream: Incidents"],
        },
      ],
    },
    isLoading: false,
    isError: false,
  }),
  useDashboardFeedHealthQuery: () => ({
    data: {
      status: "ready",
      reason: null,
      dependency_spec: null,
      last_updated_at: new Date().toISOString(),
      stale_feed_count: 2,
      error_feed_count: 1,
      oldest_success_age_hours: 5.5,
      queue_lag: { unavailable_reason: "Worker queue metrics are not available yet." },
    },
    isLoading: false,
    isError: false,
  }),
  useDashboardSavedFollowupQuery: () => ({
    data: {
      status: "ready",
      reason: null,
      dependency_spec: null,
      last_updated_at: new Date().toISOString(),
      saved_count: 3,
      latest_items: [
        {
          article_id: "s1",
          title: "Saved article",
          feed_title: "Test Feed",
          canonical_url: "https://example.com/s1",
          published_at: new Date().toISOString(),
          saved_at: new Date().toISOString(),
        },
      ],
    },
    isLoading: false,
    isError: false,
  }),
  useDashboardMonitoringSignalsQuery: () => ({
    data: {
      status: "ready",
      reason: null,
      dependency_spec: null,
      last_updated_at: new Date().toISOString(),
      window_hours: 24,
      streams: [
        {
          stream_id: "st1",
          stream_name: "Incidents",
          signal_score: 75,
          matched_count_window: 5,
          unread_count_window: 3,
          confidence_summary: { average_confidence: null, classifier_run_count: 0 },
          latest_match_at: new Date().toISOString(),
          score_breakdown: { recent_matches: 50, unread_matches: 15, stream_priority: 10 },
        },
      ],
    },
    isLoading: false,
    isError: false,
  }),
  useDashboardDiscoveryCandidatesQuery: () => ({
    data: {
      status: "ready",
      reason: null,
      dependency_spec: null,
      last_updated_at: new Date().toISOString(),
      pending_recommendation_count: 4,
      monitoring_candidate_count: 0,
      candidates: [
        {
          article_id: null,
          recommendation_id: "r1",
          title: "Pending Feed",
          canonical_url: "https://example.com/feed.xml",
          source_kind: "feed_recommendation" as const,
          candidate_score: 55,
          why_candidate: ["Pending feed recommendation from query: python"],
        },
      ],
    },
    isLoading: false,
    isError: false,
  }),
  useDashboardTrendsQuery: () => ({
    data: {
      status: "ready",
      reason: null,
      dependency_spec: null,
      last_updated_at: new Date().toISOString(),
      window_hours: 24,
      baseline_days: 14,
      topics: [
        {
          topic: "rust",
          momentum_score: 7.5,
          short_window_count: 5,
          baseline_count: 0,
          source_diversity_count: 2,
          representative_article_ids: ["a1", "a2"],
        },
      ],
    },
    isLoading: false,
    isError: false,
  }),
}));

import type { DashboardCardRegistration } from "./DashboardHost";
import { DashboardHost } from "./DashboardHost";

describe("DashboardHost", () => {
  it("renders loading and error states", () => {
    const { rerender } = render(<DashboardHost summary={undefined} isLoading isError={false} />);
    expect(screen.getByText("Loading dashboard…")).toBeVisible();

    rerender(<DashboardHost summary={undefined} isLoading={false} isError />);
    expect(screen.getByText("Failed to load dashboard summary.")).toBeVisible();
  });

  it("renders ready and unavailable cards deterministically", () => {
    render(
      <DashboardHost
        isLoading={false}
        isError={false}
        summary={{
          last_updated_at: new Date().toISOString(),
          cards: [
            {
              id: "saved_followup",
              title: "Saved follow-up",
              status: "ready",
            },
            {
              id: "trends",
              title: "Trends",
              status: "unavailable",
              reason: "Trends pipeline unavailable",
              dependency_spec: "docs/specs/trends-detection-dashboard-v1.md",
            },
          ],
        }}
      />
    );

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    // Saved follow-up card should show data from mocked hook
    expect(screen.getByText("3 saved")).toBeVisible();
    expect(screen.getByText("Saved article")).toBeVisible();
    // Trends card is unavailable — should show fallback
    expect(screen.getByText("Trends pipeline unavailable")).toBeVisible();
    expect(screen.getByText("Dependency: docs/specs/trends-detection-dashboard-v1.md")).toBeVisible();
  });

  it("isolates ready-card render failures behind card unavailable fallback", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const throwingRegistry: Record<string, DashboardCardRegistration> = {
      saved_followup: {
        id: "saved_followup",
        title: "Saved follow-up",
        source: "plugin",
        mount: () => {
          throw new Error("card boom");
        },
      },
    };

    try {
      render(
        <DashboardHost
          isLoading={false}
          isError={false}
          registryById={throwingRegistry}
          summary={{
            last_updated_at: new Date().toISOString(),
            cards: [
              {
                id: "saved_followup",
                title: "Saved follow-up",
                status: "ready",
              },
            ],
          }}
        />
      );
      expect(screen.getByText("Card unavailable")).toBeVisible();
    } finally {
      consoleSpy.mockRestore();
    }
  });
});