import { Alert, Box, Button, Divider, Paper, Stack, Typography } from "@mui/material";
import { useState } from "react";

import { formatRelativeTime } from "../lib/time";
import type { ArticleDetail, ArticleListItem } from "../../../shared/types/contracts";

type ReaderPaneProps = {
  selectedArticle: ArticleListItem | undefined;
  selectedArticleId: string;
  streamNameById: Record<string, string>;
  detail: ArticleDetail | undefined;
  contentHtml: string;
  isLoading: boolean;
  isError: boolean;
  isMutating: boolean;
  hasMutationError: boolean;
  onToggleRead: () => void;
  onToggleSaved: () => void;
  onOpenOriginal: () => void;
  onMoveSelection: (delta: number) => void;
  onBackToList?: () => void;
};

type EvidenceRecord = Record<string, unknown>;

const asRecord = (value: unknown): EvidenceRecord | null => {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as EvidenceRecord;
};

const firstRecord = (value: unknown): EvidenceRecord | null => {
  if (!Array.isArray(value) || value.length === 0) {
    return null;
  }
  return asRecord(value[0]);
};

const buildEvidenceSummary = (reason: string | undefined, rawEvidence: unknown): string | null => {
  const evidence = asRecord(rawEvidence);
  if (!evidence) {
    return null;
  }

  const parts: string[] = [];
  if (reason) {
    parts.push(reason);
  }

  const matcherType = typeof evidence.matcher_type === "string" ? evidence.matcher_type : "";
  const ruleEvidence = matcherType === "hybrid" ? asRecord(evidence.rules) : evidence;
  const classifierEvidence = matcherType === "hybrid" ? asRecord(evidence.classifier) : evidence;

  const keywordHit = firstRecord(ruleEvidence?.keyword_hits);
  if (keywordHit) {
    const value = typeof keywordHit.value === "string" ? keywordHit.value : "keyword";
    const snippet = typeof keywordHit.snippet === "string" ? keywordHit.snippet : "";
    parts.push(`keyword "${value}"${snippet ? ` in "${snippet}"` : ""}`);
  }

  const regexHit = firstRecord(ruleEvidence?.regex_hits);
  if (regexHit) {
    const pattern = typeof regexHit.pattern === "string" ? regexHit.pattern : "regex";
    const snippet = typeof regexHit.snippet === "string" ? regexHit.snippet : "";
    parts.push(`regex /${pattern}/${snippet ? ` in "${snippet}"` : ""}`);
  }

  if (ruleEvidence && "query" in ruleEvidence) {
    parts.push("query expression matched");
  }

  const classifier = asRecord(classifierEvidence);
  const classifierPlugin = classifier && typeof classifier.plugin === "string" ? classifier.plugin : "";
  const classifierReason = classifier && typeof classifier.reason === "string" ? classifier.reason : "";
  const classifierConfidence =
    classifier && typeof classifier.confidence === "number" ? classifier.confidence.toFixed(2) : "";
  if (classifierPlugin || classifierReason || classifierConfidence) {
    const classifierParts = [classifierPlugin, classifierReason, classifierConfidence ? `confidence ${classifierConfidence}` : ""]
      .filter(Boolean)
      .join(", ");
    parts.push(`classifier (${classifierParts})`);
  }

  if (parts.length === 0) {
    return null;
  }
  return parts.join(" | ");
};

const escapeRegExp = (value: string): string => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const extractHighlightTerms = (
  streamIds: string[],
  streamMatchEvidence: Record<string, { [key: string]: unknown }> | null
): string[] => {
  if (!streamMatchEvidence) {
    return [];
  }

  const seen = new Set<string>();
  const terms: string[] = [];

  const addTerm = (value: unknown) => {
    if (typeof value !== "string") {
      return;
    }
    const normalized = value.trim();
    if (!normalized) {
      return;
    }
    const key = normalized.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    terms.push(normalized);
  };

  for (const streamId of streamIds) {
    const evidence = asRecord(streamMatchEvidence[streamId]);
    if (!evidence) {
      continue;
    }

    const matcherType = typeof evidence.matcher_type === "string" ? evidence.matcher_type : "";
    const rulesEvidence = matcherType === "hybrid" ? asRecord(evidence.rules) : evidence;
    if (!rulesEvidence) {
      continue;
    }

    const keywordHits = Array.isArray(rulesEvidence.keyword_hits) ? rulesEvidence.keyword_hits : [];
    for (const hit of keywordHits) {
      addTerm(asRecord(hit)?.value);
    }

    const regexHits = Array.isArray(rulesEvidence.regex_hits) ? rulesEvidence.regex_hits : [];
    for (const hit of regexHits) {
      addTerm(asRecord(hit)?.value);
    }
  }

  return terms;
};

const highlightHtmlByTerms = (html: string, terms: string[]): string => {
  if (!html || terms.length === 0) {
    return html;
  }

  const normalizedTerms = terms
    .map((term) => term.trim())
    .filter(Boolean)
    .sort((left, right) => right.length - left.length);
  if (normalizedTerms.length === 0) {
    return html;
  }

  const pattern = new RegExp(`(${normalizedTerms.map((term) => escapeRegExp(term)).join("|")})`, "gi");
  const container = document.createElement("div");
  container.innerHTML = html;

  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const textNodes: Text[] = [];
  while (walker.nextNode()) {
    const node = walker.currentNode as Text;
    const parentTag = node.parentElement?.tagName ?? "";
    if (!node.nodeValue?.trim()) {
      continue;
    }
    if (parentTag === "MARK" || parentTag === "CODE" || parentTag === "PRE" || parentTag === "SCRIPT" || parentTag === "STYLE") {
      continue;
    }
    textNodes.push(node);
  }

  for (const node of textNodes) {
    const text = node.nodeValue ?? "";
    pattern.lastIndex = 0;
    if (!pattern.test(text)) {
      continue;
    }

    pattern.lastIndex = 0;
    const fragment = document.createDocumentFragment();
    let lastIndex = 0;
    let match = pattern.exec(text);
    while (match) {
      const [value] = match;
      const start = match.index;
      const end = start + value.length;
      if (start > lastIndex) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex, start)));
      }
      const mark = document.createElement("mark");
      mark.className = "workspace-reader__highlight";
      mark.textContent = text.slice(start, end);
      fragment.appendChild(mark);
      lastIndex = end;
      match = pattern.exec(text);
    }
    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
    }
    node.parentNode?.replaceChild(fragment, node);
  }

  return container.innerHTML;
};

export function ReaderPane({
  selectedArticle,
  selectedArticleId,
  streamNameById,
  detail,
  contentHtml,
  isLoading,
  isError,
  isMutating,
  hasMutationError,
  onToggleRead,
  onToggleSaved,
  onOpenOriginal,
  onMoveSelection,
  onBackToList,
}: ReaderPaneProps) {
  const streamIds = detail?.stream_ids ?? selectedArticle?.stream_ids ?? [];
  const matchedStreamNames = streamIds
    .map((streamId) => streamNameById[streamId])
    .filter((name): name is string => Boolean(name));
  const streamMatchReasons = detail?.stream_match_reasons ?? selectedArticle?.stream_match_reasons ?? null;
  const streamMatchEvidence = detail?.stream_match_evidence ?? selectedArticle?.stream_match_evidence ?? null;
  const highlightTerms = extractHighlightTerms(streamIds, streamMatchEvidence);
  const [showHighlights, setShowHighlights] = useState(true);
  const renderedContentHtml = showHighlights ? highlightHtmlByTerms(contentHtml, highlightTerms) : contentHtml;

  const matchedReasonSummaries = streamIds
    .map((streamId) => {
      const streamName = streamNameById[streamId];
      const reason = streamMatchReasons?.[streamId];
      if (!streamName || !reason) {
        return null;
      }
      return `${streamName}: ${reason}`;
    })
    .filter((value): value is string => Boolean(value));
  const matchedEvidenceSummaries = streamIds
    .map((streamId) => {
      const streamName = streamNameById[streamId];
      if (!streamName) {
        return null;
      }
      const summary = buildEvidenceSummary(streamMatchReasons?.[streamId], streamMatchEvidence?.[streamId]);
      if (!summary) {
        return null;
      }
      return `${streamName}: ${summary}`;
    })
    .filter((value): value is string => Boolean(value));

  return (
    <Paper className="workspace-reader" component="section" elevation={0}>
      {!selectedArticleId ? (
        <Typography variant="body2" color="text.secondary">
          Select an article to open the reader.
        </Typography>
      ) : null}

      {isLoading ? <Typography color="text.secondary">Loading article...</Typography> : null}
      {isError ? <Alert severity="error">Failed to load article details.</Alert> : null}
      {hasMutationError ? <Alert severity="error">Failed to update article state.</Alert> : null}

      {detail ? (
        <Stack spacing={2}>
          <Box className="workspace-reader__top">
            {onBackToList ? (
              <Box>
                <Button size="small" variant="text" onClick={onBackToList}>
                  Back to list
                </Button>
              </Box>
            ) : null}

            <Box>
              <Typography variant="h4" className="workspace-reader__title">
                {detail.title || "Untitled article"}
              </Typography>
              <Typography variant="body2" color="text.secondary" className="workspace-reader__meta">
                {detail.feed_title || "Unknown source"}
                {detail.published_at ? ` · ${formatRelativeTime(detail.published_at)}` : ""}
              </Typography>
              {matchedStreamNames.length > 0 ? (
                <Typography variant="body2" className="workspace-reader__match">
                  Matched by monitoring feeds: {matchedStreamNames.join(", ")}
                </Typography>
              ) : null}
              {matchedReasonSummaries.length > 0 ? (
                <Typography variant="body2" className="workspace-reader__match">
                  Why matched: {matchedReasonSummaries.join(" · ")}
                </Typography>
              ) : null}
              {matchedEvidenceSummaries.length > 0 ? (
                <Typography variant="body2" className="workspace-reader__match">
                  Match evidence: {matchedEvidenceSummaries.join(" · ")}
                </Typography>
              ) : null}
            </Box>

            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap className="workspace-reader__actions">
              <Button size="small" variant="outlined" disabled={isMutating} onClick={onToggleRead}>
                {selectedArticle?.is_read ? "Mark unread" : "Mark read"}
              </Button>
              <Button size="small" variant="outlined" disabled={isMutating} onClick={onToggleSaved}>
                {selectedArticle?.is_starred ? "Unsave" : "Save"}
              </Button>
              <Button size="small" variant="outlined" onClick={onOpenOriginal} disabled={!detail.canonical_url}>
                Open original
              </Button>
              <Button size="small" variant="text" onClick={() => onMoveSelection(-1)}>
                Prev
              </Button>
              <Button size="small" variant="text" onClick={() => onMoveSelection(1)}>
                Next
              </Button>
              {contentHtml && highlightTerms.length > 0 ? (
                <Button size="small" variant="text" onClick={() => setShowHighlights((current) => !current)}>
                  {showHighlights ? "Hide highlights" : "Show highlights"}
                </Button>
              ) : null}
            </Stack>
          </Box>

          <Divider />

          {renderedContentHtml ? (
            <Box
              className="workspace-reader__body"
              dangerouslySetInnerHTML={{ __html: renderedContentHtml }}
            />
          ) : (
            <Typography variant="body1" className="workspace-reader__empty">
              No content available.
            </Typography>
          )}
        </Stack>
      ) : null}
    </Paper>
  );
}
