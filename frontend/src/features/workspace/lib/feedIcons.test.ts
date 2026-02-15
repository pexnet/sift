import { describe, expect, it } from "vitest";

import type { Feed } from "../../../shared/types/contracts";
import { getFeedAvatarHue, getFeedIconUrl, getFeedInitial } from "./feedIcons";

function feedStub(patch: Partial<Feed>): Feed {
  return {
    id: "7b178ec6-c1aa-40f8-813e-d4f13f38ac26",
    owner_id: "6fb7fb76-ed95-46f1-9d5b-90e876d0267b",
    folder_id: null,
    title: "Sample Feed",
    url: "https://example.com/rss.xml",
    site_url: null,
    is_active: true,
    fetch_interval_minutes: 15,
    etag: null,
    last_modified: null,
    last_fetched_at: null,
    last_fetch_error: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...patch,
  };
}

describe("feedIcons", () => {
  it("builds favicon url from site_url when available", () => {
    const url = getFeedIconUrl(feedStub({ site_url: "https://news.example.org/home", url: "https://other.test/rss" }));
    expect(url).toBe("https://news.example.org/favicon.ico");
  });

  it("falls back to feed url when site_url is missing", () => {
    const url = getFeedIconUrl(feedStub({ site_url: null, url: "https://rss.example.net/feed.xml" }));
    expect(url).toBe("https://rss.example.net/favicon.ico");
  });

  it("returns null for invalid urls", () => {
    const url = getFeedIconUrl(feedStub({ site_url: "bad-url", url: "also-bad" }));
    expect(url).toBeNull();
  });

  it("returns deterministic initial and hue for fallback avatars", () => {
    expect(getFeedInitial("dark reading")).toBe("D");
    expect(getFeedAvatarHue("dark reading")).toBe(getFeedAvatarHue("dark reading"));
  });
});
