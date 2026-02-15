import type { Feed } from "../../../shared/types/contracts";

function toHostname(input: string | null | undefined): string | null {
  if (!input) {
    return null;
  }
  try {
    return new URL(input).hostname || null;
  } catch {
    return null;
  }
}

export function getFeedIconUrl(feed: Feed): string | null {
  const hostname = toHostname(feed.site_url) ?? toHostname(feed.url);
  if (!hostname) {
    return null;
  }
  return `https://${hostname}/favicon.ico`;
}

export function getFeedInitial(title: string): string {
  const trimmed = title.trim();
  if (!trimmed) {
    return "?";
  }
  const first = Array.from(trimmed)[0] ?? "?";
  return first.toUpperCase();
}

export function getFeedAvatarHue(seed: string): number {
  let hash = 0;
  for (const char of seed) {
    hash = (hash << 5) - hash + char.charCodeAt(0);
    hash |= 0;
  }
  return Math.abs(hash) % 360;
}
