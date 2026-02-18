import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReaderPane } from "./ReaderPane";

describe("ReaderPane", () => {
  it("wires core reader actions", () => {
    const onToggleRead = vi.fn();
    const onToggleSaved = vi.fn();
    const onOpenOriginal = vi.fn();
    const onMoveSelection = vi.fn();

    render(
      <ReaderPane
        selectedArticle={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          title: "Reader title",
          canonical_url: "https://example.com/article",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{}}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Body",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        contentHtml="<p>Body</p>"
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={onToggleRead}
        onToggleSaved={onToggleSaved}
        onOpenOriginal={onOpenOriginal}
        onMoveSelection={onMoveSelection}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Mark read/i }));
    fireEvent.click(screen.getByRole("button", { name: /Save/i }));
    fireEvent.click(screen.getByRole("button", { name: /Open original/i }));
    fireEvent.click(screen.getByRole("button", { name: /Prev/i }));
    fireEvent.click(screen.getByRole("button", { name: /Next/i }));

    expect(screen.getByText("Body")).toBeVisible();
    expect(onToggleRead).toHaveBeenCalledTimes(1);
    expect(onToggleSaved).toHaveBeenCalledTimes(1);
    expect(onOpenOriginal).toHaveBeenCalledTimes(1);
    expect(onMoveSelection).toHaveBeenNthCalledWith(1, -1);
    expect(onMoveSelection).toHaveBeenNthCalledWith(2, 1);
  });

  it("renders back-to-list action when provided", () => {
    const onBackToList = vi.fn();

    render(
      <ReaderPane
        selectedArticle={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          title: "Reader title",
          canonical_url: "https://example.com/article",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{}}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Body",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        contentHtml="<p>Body</p>"
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
        onBackToList={onBackToList}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Back to list/i }));
    expect(onBackToList).toHaveBeenCalledTimes(1);
  });

  it("shows empty placeholder when sanitized content is empty", () => {
    render(
      <ReaderPane
        selectedArticle={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          title: "Reader title",
          canonical_url: "https://example.com/article",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{}}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Body",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        contentHtml=""
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
      />
    );

    expect(screen.getByText("No content available.")).toBeVisible();
  });

  it("renders reader body container with editorial class hooks", () => {
    render(
      <ReaderPane
        selectedArticle={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          title: "Reader title",
          canonical_url: "https://example.com/article",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{}}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Body",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: [],
        }}
        contentHtml="<p>Body</p>"
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
      />
    );

    expect(document.querySelector(".workspace-reader")).toBeTruthy();
    expect(document.querySelector(".workspace-reader__body")).toBeTruthy();
  });

  it("shows monitoring match explainability in reader metadata", () => {
    render(
      <ReaderPane
        selectedArticle={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          title: "Reader title",
          canonical_url: "https://example.com/article",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: ["d76760f1-ba73-416b-8b4c-a70f1734720f"],
          stream_match_reasons: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": "keyword: darktrace",
          },
          stream_match_evidence: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": {
              matcher_type: "rules",
              keyword_hits: [
                {
                  field: "title",
                  value: "darktrace",
                  start: 0,
                  end: 9,
                  snippet: "Darktrace deep dive",
                },
              ],
            },
          },
        }}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{
          "d76760f1-ba73-416b-8b4c-a70f1734720f": "darktrace",
        }}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Body",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: ["d76760f1-ba73-416b-8b4c-a70f1734720f"],
          stream_match_reasons: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": "keyword: darktrace",
          },
          stream_match_evidence: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": {
              matcher_type: "rules",
              keyword_hits: [
                {
                  field: "title",
                  value: "darktrace",
                  start: 0,
                  end: 9,
                  snippet: "Darktrace deep dive",
                },
              ],
            },
          },
        }}
        contentHtml="<p>Body</p>"
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
      />
    );

    expect(screen.getByText("Matched by monitoring feeds: darktrace")).toBeVisible();
    expect(screen.getByText("Why matched: darktrace: keyword: darktrace")).toBeVisible();
    expect(screen.getByText("Matched terms: darktrace (title)")).toBeVisible();
    expect(
      screen.getByText(
        'Match evidence: darktrace: keyword: darktrace | keyword "darktrace" in "Darktrace deep dive"'
      )
    ).toBeVisible();
  });

  it("renders classifier findings in summaries and evidence rows", () => {
    render(
      <ReaderPane
        selectedArticle={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          title: "Reader title",
          canonical_url: "https://example.com/article",
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: ["d76760f1-ba73-416b-8b4c-a70f1734720f"],
          stream_match_reasons: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": "classifier: high relevance",
          },
          stream_match_evidence: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": {
              matcher_type: "classifier",
              plugin: "keyword_heuristic_classifier",
              reason: "high relevance",
              confidence: 0.92,
              findings: [
                {
                  label: "entity hit",
                  field: "content_text",
                  start: 0,
                  end: 12,
                  text: "Threat actor",
                  score: 0.91,
                },
                {
                  label: "taxonomy",
                  text: "APT behavior observed",
                  score: 0.78,
                },
              ],
            },
          },
        }}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{
          "d76760f1-ba73-416b-8b4c-a70f1734720f": "sec-stream",
        }}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Threat actor details and timeline.",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: ["d76760f1-ba73-416b-8b4c-a70f1734720f"],
          stream_match_reasons: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": "classifier: high relevance",
          },
          stream_match_evidence: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": {
              matcher_type: "classifier",
              plugin: "keyword_heuristic_classifier",
              reason: "high relevance",
              confidence: 0.92,
              findings: [
                {
                  label: "entity hit",
                  field: "content_text",
                  start: 0,
                  end: 12,
                  text: "Threat actor",
                  score: 0.91,
                },
                {
                  label: "taxonomy",
                  text: "APT behavior observed",
                  score: 0.78,
                },
              ],
            },
          },
        }}
        contentHtml="<p>Threat actor details and timeline.</p>"
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
      />
    );

    expect(screen.getByText(/Match evidence: sec-stream:/)).toBeVisible();
    expect(screen.getByText(/findings 2/i)).toBeVisible();
    expect(screen.getByText("sec-stream: entity hit (score 0.91) (content)")).toBeVisible();
    expect(screen.getByText("APT behavior observed")).toBeVisible();
    expect(screen.getAllByRole("button", { name: /Jump to highlight/i }).length).toBeGreaterThan(0);
  });

  it("highlights matched terms in reader body and allows toggling highlights", () => {
    const { container } = render(
      <ReaderPane
        selectedArticle={undefined}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{
          "d76760f1-ba73-416b-8b4c-a70f1734720f": "darktrace",
        }}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Darktrace details.",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: ["d76760f1-ba73-416b-8b4c-a70f1734720f"],
          stream_match_reasons: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": "keyword: darktrace",
          },
          stream_match_evidence: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": {
              matcher_type: "rules",
              keyword_hits: [
                {
                  field: "content_text",
                  value: "darktrace",
                  start: 0,
                  end: 9,
                  snippet: "Darktrace details",
                },
              ],
            },
          },
        }}
        contentHtml="<p>Darktrace details from stream match.</p>"
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: /Hide highlights/i })).toBeVisible();
    expect(container.querySelectorAll("mark.workspace-reader__highlight").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /Hide highlights/i }));
    expect(screen.getByRole("button", { name: /Show highlights/i })).toBeVisible();
    expect(container.querySelectorAll("mark.workspace-reader__highlight").length).toBe(0);
  });

  it("renders query-hit rows and highlights title spans", () => {
    const { container } = render(
      <ReaderPane
        selectedArticle={undefined}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{
          "d76760f1-ba73-416b-8b4c-a70f1734720f": "sec-stream",
        }}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Darktrace response guidance",
          content_text: "Coverage includes SentinelOne telemetry and response context.",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: ["d76760f1-ba73-416b-8b4c-a70f1734720f"],
          stream_match_reasons: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": "query matched",
          },
          stream_match_evidence: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": {
              matcher_type: "rules",
              query: { expression: true },
              query_hits: [
                {
                  field: "title",
                  token: "Darktrace",
                  start: 0,
                  end: 9,
                  snippet: "Darktrace response guidance",
                },
                {
                  field: "content_text",
                  token: "SentinelOne",
                  start: 18,
                  end: 29,
                  snippet: "Coverage includes SentinelOne telemetry",
                },
              ],
            },
          },
        }}
        contentHtml="<p>Coverage includes SentinelOne telemetry and response context.</p>"
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
      />
    );

    expect(screen.getByText("Matched terms: Darktrace (title), SentinelOne (content)")).toBeVisible();
    expect(screen.getByText('sec-stream: Query hit: "Darktrace" (title)')).toBeVisible();
    expect(screen.getByText('sec-stream: Query hit: "SentinelOne" (content)')).toBeVisible();
    expect(container.querySelectorAll(".workspace-reader__title mark.workspace-reader__highlight").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /Hide highlights/i }));
    expect(container.querySelectorAll(".workspace-reader__title mark.workspace-reader__highlight").length).toBe(0);
  });

  it("renders evidence rows with jump-to-highlight action", () => {
    const scrollIntoViewMock = vi.fn();
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      value: scrollIntoViewMock,
      configurable: true,
      writable: true,
    });

    render(
      <ReaderPane
        selectedArticle={undefined}
        selectedArticleId="b67cb366-41e1-4114-8fa0-07ec799f1968"
        streamNameById={{
          "d76760f1-ba73-416b-8b4c-a70f1734720f": "darktrace",
        }}
        detail={{
          id: "b67cb366-41e1-4114-8fa0-07ec799f1968",
          feed_id: null,
          feed_title: "CyberChef",
          source_id: "source",
          canonical_url: "https://example.com/article",
          title: "Reader title",
          content_text: "Darktrace details.",
          language: null,
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          is_read: false,
          is_starred: false,
          is_archived: false,
          stream_ids: ["d76760f1-ba73-416b-8b4c-a70f1734720f"],
          stream_match_reasons: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": "keyword: darktrace",
          },
          stream_match_evidence: {
            "d76760f1-ba73-416b-8b4c-a70f1734720f": {
              matcher_type: "rules",
              keyword_hits: [
                {
                  field: "content_text",
                  value: "darktrace",
                  start: 0,
                  end: 9,
                  snippet: "Darktrace details",
                },
              ],
            },
          },
        }}
        contentHtml="<p>Darktrace details from stream match.</p>"
        isLoading={false}
        isError={false}
        isMutating={false}
        hasMutationError={false}
        onToggleRead={vi.fn()}
        onToggleSaved={vi.fn()}
        onOpenOriginal={vi.fn()}
        onMoveSelection={vi.fn()}
      />
    );

    expect(screen.getByText("Evidence details")).toBeVisible();
    const jumpButton = screen.getByRole("button", { name: /Jump to highlight/i });
    expect(jumpButton).toBeVisible();
    fireEvent.click(jumpButton);
    expect(scrollIntoViewMock).toHaveBeenCalledTimes(1);
  });
});
