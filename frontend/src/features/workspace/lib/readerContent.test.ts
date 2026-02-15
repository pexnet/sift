import { describe, expect, it } from "vitest";

import { isLikelyHtml, sanitizeArticleHtml, toReaderHtml } from "./readerContent";

describe("readerContent", () => {
  it("strips unsafe tags and attributes", () => {
    const result = sanitizeArticleHtml(
      `<p>Hello</p><script>alert("xss")</script><a href="javascript:alert(1)" onclick="evil()">bad</a>`
    );

    expect(result).toContain("<p>Hello</p>");
    expect(result).not.toContain("<script");
    expect(result).not.toContain("onclick=");
    expect(result).not.toContain("javascript:");
  });

  it("preserves semantic formatting tags", () => {
    const result = sanitizeArticleHtml(
      `<h2>Heading</h2><p>Paragraph</p><ul><li>One</li><li>Two</li></ul><blockquote>Quote</blockquote>`
    );

    expect(result).toContain("<h2>Heading</h2>");
    expect(result).toContain("<p>Paragraph</p>");
    expect(result).toContain("<ul>");
    expect(result).toContain("<li>One</li>");
    expect(result).toContain("<blockquote>Quote</blockquote>");
  });

  it("normalizes plaintext to readable paragraphs", () => {
    const result = toReaderHtml("first line\nsecond line\n\nnext paragraph");

    expect(result).toContain("<p>first line<br>second line</p>");
    expect(result).toContain("<p>next paragraph</p>");
  });

  it("normalizes link targets and rel attributes", () => {
    const result = sanitizeArticleHtml(`<p><a href="https://example.com/page">Visit</a></p>`);

    expect(result).toContain(`href="https://example.com/page"`);
    expect(result).toContain(`target="_blank"`);
    expect(result).toContain(`rel="noopener noreferrer"`);
  });

  it("detects likely html payloads", () => {
    expect(isLikelyHtml("<p>test</p>")).toBe(true);
    expect(isLikelyHtml("plain text")).toBe(false);
  });
});
