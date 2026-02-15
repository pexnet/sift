import { describe, expect, it } from "vitest";

import { getReadToggleDecision } from "./readActions";

describe("getReadToggleDecision", () => {
  it("returns mark-read payload and auto-advance for unread articles", () => {
    const decision = getReadToggleDecision({
      id: "11111111-1111-1111-1111-111111111111",
      feed_id: null,
      feed_title: "Feed",
      title: "Article",
      canonical_url: null,
      published_at: null,
      created_at: new Date().toISOString(),
      is_read: false,
      is_starred: false,
      is_archived: false,
      stream_ids: [],
    });

    expect(decision).toEqual({
      payload: { is_read: true },
      shouldAdvance: true,
    });
  });

  it("returns mark-unread payload without auto-advance for already-read articles", () => {
    const decision = getReadToggleDecision({
      id: "11111111-1111-1111-1111-111111111111",
      feed_id: null,
      feed_title: "Feed",
      title: "Article",
      canonical_url: null,
      published_at: null,
      created_at: new Date().toISOString(),
      is_read: true,
      is_starred: false,
      is_archived: false,
      stream_ids: [],
    });

    expect(decision).toEqual({
      payload: { is_read: false },
      shouldAdvance: false,
    });
  });

  it("returns null when no article is selected", () => {
    expect(getReadToggleDecision(undefined)).toBeNull();
  });
});
