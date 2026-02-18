import BookmarkBorderRoundedIcon from "@mui/icons-material/BookmarkBorderRounded";
import BookmarkRoundedIcon from "@mui/icons-material/BookmarkRounded";
import DoneRoundedIcon from "@mui/icons-material/DoneRounded";
import MarkEmailUnreadRoundedIcon from "@mui/icons-material/MarkEmailUnreadRounded";
import NavigateBeforeRoundedIcon from "@mui/icons-material/NavigateBeforeRounded";
import NavigateNextRoundedIcon from "@mui/icons-material/NavigateNextRounded";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import VisibilityOffRoundedIcon from "@mui/icons-material/VisibilityOffRounded";
import VisibilityRoundedIcon from "@mui/icons-material/VisibilityRounded";
import { Alert, Box, Button, Divider, IconButton, Paper, Stack, Tooltip, Typography } from "@mui/material";
import { type ReactNode, useState } from "react";

import { buildMatchedTermsSummary } from "../lib/matchEvidence";
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
type HighlightRange = {
  id: string;
  start: number;
  end: number;
};
type EvidenceRow = {
  id: string;
  streamName: string;
  title: string;
  snippet: string | null;
  markerId: string | null;
};
type EvidenceModel = {
  rows: EvidenceRow[];
  ranges: HighlightRange[];
  titleRanges: HighlightRange[];
  terms: string[];
  titleTerms: string[];
};
type OffsetHighlightResult = {
  html: string;
  appliedMarkerIds: Set<string>;
};
const EMPTY_EVIDENCE_MODEL: EvidenceModel = { rows: [], ranges: [], titleRanges: [], terms: [], titleTerms: [] };

const SKIP_HIGHLIGHT_TAGS = new Set(["MARK", "CODE", "PRE", "SCRIPT", "STYLE"]);

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

const toNumber = (value: unknown): number | null => {
  if (typeof value !== "number" || Number.isNaN(value) || !Number.isFinite(value)) {
    return null;
  }
  return value;
};

const toString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim();
  return normalized || null;
};

const normalizeFieldLabel = (field: string): string => (field === "content_text" ? "content" : field);

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
  const queryHit = firstRecord(ruleEvidence?.query_hits);
  if (queryHit) {
    const token = toString(queryHit.token) ?? toString(queryHit.value) ?? "query token";
    const field = normalizeFieldLabel(toString(queryHit.field) ?? "content_text");
    const snippet = toString(queryHit.snippet);
    parts.push(`query "${token}" (${field})${snippet ? ` in "${snippet}"` : ""}`);
  }

  const classifier = asRecord(classifierEvidence);
  const classifierPlugin = classifier && typeof classifier.plugin === "string" ? classifier.plugin : "";
  const classifierReason = classifier && typeof classifier.reason === "string" ? classifier.reason : "";
  const classifierConfidence =
    classifier && typeof classifier.confidence === "number" ? classifier.confidence.toFixed(2) : "";
  const classifierFindings = classifier && Array.isArray(classifier.findings) ? classifier.findings : [];
  if (classifierPlugin || classifierReason || classifierConfidence) {
    const classifierParts = [classifierPlugin, classifierReason, classifierConfidence ? `confidence ${classifierConfidence}` : ""]
      .filter(Boolean)
      .join(", ");
    parts.push(`classifier (${classifierParts})`);
  }
  if (classifierFindings.length > 0) {
    const firstFinding = asRecord(classifierFindings[0]);
    const findingLabel = toString(firstFinding?.label);
    const findingText = toString(firstFinding?.text) ?? toString(firstFinding?.snippet) ?? toString(firstFinding?.value);
    const findingScore = toNumber(firstFinding?.score);
    const findingSummary = [findingLabel, findingText, findingScore !== null ? `score ${findingScore.toFixed(2)}` : ""]
      .filter(Boolean)
      .join(", ");
    parts.push(`findings ${classifierFindings.length}${findingSummary ? ` (${findingSummary})` : ""}`);
  }

  if (parts.length === 0) {
    return null;
  }
  return parts.join(" | ");
};

const escapeRegExp = (value: string): string => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const addUniqueTerm = (terms: string[], seenTerms: Set<string>, value: string | null) => {
  if (!value) {
    return;
  }
  const normalized = value.toLowerCase();
  if (seenTerms.has(normalized)) {
    return;
  }
  seenTerms.add(normalized);
  terms.push(value);
};

const createEvidenceModel = (
  streamIds: string[],
  streamNameById: Record<string, string>,
  streamMatchEvidence: Record<string, { [key: string]: unknown }> | null
): EvidenceModel => {
  const rows: EvidenceRow[] = [];
  const ranges: HighlightRange[] = [];
  const titleRanges: HighlightRange[] = [];
  const terms: string[] = [];
  const titleTerms: string[] = [];
  const seenTerms = new Set<string>();
  const seenTitleTerms = new Set<string>();

  for (const streamId of streamIds) {
    const streamName = streamNameById[streamId];
    if (!streamName) {
      continue;
    }
    const evidence = asRecord(streamMatchEvidence?.[streamId]);
    if (!evidence) {
      continue;
    }

    const matcherType = typeof evidence.matcher_type === "string" ? evidence.matcher_type : "";
    const rulesEvidence = matcherType === "hybrid" ? asRecord(evidence.rules) : evidence;
    const classifierEvidence = matcherType === "hybrid" ? asRecord(evidence.classifier) : evidence;

    const pushHitRow = (
      hit: EvidenceRecord,
      options: {
        kind: "keyword" | "regex" | "query";
        streamIndex: number;
        hitIndex: number;
      }
    ) => {
      const { kind, streamIndex, hitIndex } = options;
      const field = toString(hit.field) ?? "content_text";
      const displayField = normalizeFieldLabel(field);
      const value = kind === "query" ? toString(hit.token) ?? toString(hit.value) : toString(hit.value);
      const snippet = toString(hit.snippet);
      const pattern = kind === "regex" ? toString(hit.pattern) : null;
      const start = toNumber(hit.start);
      const end = toNumber(hit.end);
      const markerId = `reader-highlight-${streamId}-${kind}-${streamIndex}-${hitIndex}`;

      if (field === "content_text" && start !== null && end !== null && end > start) {
        ranges.push({ id: markerId, start, end });
      }
      if (field === "title" && start !== null && end !== null && end > start) {
        titleRanges.push({ id: markerId, start, end });
      }
      if (value) {
        addUniqueTerm(terms, seenTerms, value);
        if (field === "title") {
          addUniqueTerm(titleTerms, seenTitleTerms, value);
        }
      }

      if (kind === "keyword") {
        rows.push({
          id: `${streamId}-keyword-${streamIndex}-${hitIndex}`,
          streamName,
          title: value ? `Keyword hit: "${value}" (${displayField})` : `Keyword hit (${displayField})`,
          snippet,
          markerId: field === "content_text" ? markerId : null,
        });
        return;
      }

      if (kind === "query") {
        rows.push({
          id: `${streamId}-query-hit-${streamIndex}-${hitIndex}`,
          streamName,
          title: value ? `Query hit: "${value}" (${displayField})` : `Query hit (${displayField})`,
          snippet,
          markerId: field === "content_text" ? markerId : null,
        });
        return;
      }

      rows.push({
        id: `${streamId}-regex-${streamIndex}-${hitIndex}`,
        streamName,
        title: pattern
          ? `Regex hit: /${pattern}/${value ? ` => "${value}"` : ""} (${displayField})`
          : `Regex hit${value ? `: "${value}"` : ""} (${displayField})`,
        snippet,
        markerId: field === "content_text" ? markerId : null,
      });
    };

    const keywordHits = Array.isArray(rulesEvidence?.keyword_hits) ? rulesEvidence.keyword_hits : [];
    keywordHits.forEach((entry, index) => {
      const hit = asRecord(entry);
      if (!hit) {
        return;
      }
      pushHitRow(hit, { kind: "keyword", streamIndex: rows.length, hitIndex: index });
    });

    const regexHits = Array.isArray(rulesEvidence?.regex_hits) ? rulesEvidence.regex_hits : [];
    regexHits.forEach((entry, index) => {
      const hit = asRecord(entry);
      if (!hit) {
        return;
      }
      pushHitRow(hit, { kind: "regex", streamIndex: rows.length, hitIndex: index });
    });

    const queryHits = Array.isArray(rulesEvidence?.query_hits) ? rulesEvidence.query_hits : [];
    queryHits.forEach((entry, index) => {
      const hit = asRecord(entry);
      if (!hit) {
        return;
      }
      pushHitRow(hit, { kind: "query", streamIndex: rows.length, hitIndex: index });
    });

    if (rulesEvidence && "query" in rulesEvidence) {
      rows.push({
        id: `${streamId}-query`,
        streamName,
        title: queryHits.length > 0 ? "Query expression matched (with spans)" : "Query expression matched",
        snippet: null,
        markerId: null,
      });
    }

    const classifier = asRecord(classifierEvidence);
    if (classifier) {
      const findingSnippetValues = new Set<string>();
      const plugin = toString(classifier.plugin);
      const confidence = toNumber(classifier.confidence);
      const reason = toString(classifier.reason);
      if (plugin || confidence !== null || reason) {
        rows.push({
          id: `${streamId}-classifier`,
          streamName,
          title: `Classifier: ${[plugin, reason, confidence !== null ? `confidence ${confidence.toFixed(2)}` : ""]
            .filter(Boolean)
            .join(" | ")}`,
          snippet: null,
          markerId: null,
        });
      }
      const classifierFindings = Array.isArray(classifier.findings) ? classifier.findings : [];
      classifierFindings.forEach((entry, index) => {
        const finding = asRecord(entry);
        if (!finding) {
          return;
        }
        const label = toString(finding.label) ?? "Classifier finding";
        const value = toString(finding.value);
        const text = toString(finding.text) ?? toString(finding.snippet) ?? value;
        const score = toNumber(finding.score);
        const field = toString(finding.field);
        const displayField = field ? normalizeFieldLabel(field) : null;
        const start = toNumber(finding.start);
        const end = toNumber(finding.end);
        const markerId = `reader-highlight-${streamId}-classifier-finding-${index}`;

        if (field === "content_text" && start !== null && end !== null && end > start) {
          ranges.push({ id: markerId, start, end });
        }
        if (field === "title" && start !== null && end !== null && end > start) {
          titleRanges.push({ id: markerId, start, end });
        }
        if (value) {
          addUniqueTerm(terms, seenTerms, value);
          if (field === "title") {
            addUniqueTerm(titleTerms, seenTitleTerms, value);
          }
        } else if (text && text.length <= 80) {
          addUniqueTerm(terms, seenTerms, text);
          if (field === "title") {
            addUniqueTerm(titleTerms, seenTitleTerms, text);
          }
        }
        if (text) {
          findingSnippetValues.add(text);
        }

        rows.push({
          id: `${streamId}-classifier-finding-${index}`,
          streamName,
          title: `${label}${score !== null ? ` (score ${score.toFixed(2)})` : ""}${displayField ? ` (${displayField})` : ""}`,
          snippet: text,
          markerId: field === "content_text" ? markerId : null,
        });
      });
      const classifierSnippets = Array.isArray(classifier.snippets) ? classifier.snippets : [];
      classifierSnippets.forEach((entry, index) => {
        const snippetRecord = asRecord(entry);
        const text = toString(snippetRecord?.text) ?? (typeof entry === "string" ? entry : null);
        if (!text || findingSnippetValues.has(text)) {
          return;
        }
        rows.push({
          id: `${streamId}-classifier-snippet-${index}`,
          streamName,
          title: "Classifier snippet",
          snippet: text,
          markerId: null,
        });
      });
    }
  }

  return { rows, ranges, titleRanges, terms, titleTerms };
};

const normalizeRanges = (ranges: HighlightRange[], contentLength: number): HighlightRange[] => {
  if (contentLength <= 0 || ranges.length === 0) {
    return [];
  }

  const sorted = ranges
    .map((range) => {
      const start = Math.max(0, Math.min(contentLength, range.start));
      const end = Math.max(0, Math.min(contentLength, range.end));
      return { ...range, start, end };
    })
    .filter((range) => range.end > range.start)
    .sort((left, right) => (left.start === right.start ? left.end - right.end : left.start - right.start));

  const normalized: HighlightRange[] = [];
  let cursor = 0;
  for (const range of sorted) {
    const start = Math.max(range.start, cursor);
    const end = range.end;
    if (end <= start) {
      continue;
    }
    normalized.push({ ...range, start, end });
    cursor = end;
  }
  return normalized;
};

const highlightHtmlByOffsets = (html: string, ranges: HighlightRange[]): OffsetHighlightResult => {
  if (!html || ranges.length === 0) {
    return { html, appliedMarkerIds: new Set<string>() };
  }

  const container = document.createElement("div");
  container.innerHTML = html;
  const contentLength = (container.textContent ?? "").length;
  const normalizedRanges = normalizeRanges(ranges, contentLength);
  if (normalizedRanges.length === 0) {
    return { html, appliedMarkerIds: new Set<string>() };
  }

  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const textNodes: Array<{ node: Text; start: number; end: number; highlightable: boolean }> = [];
  let cursor = 0;
  while (walker.nextNode()) {
    const node = walker.currentNode as Text;
    const text = node.nodeValue ?? "";
    if (text.length === 0) {
      continue;
    }
    const parentTag = node.parentElement?.tagName ?? "";
    textNodes.push({
      node,
      start: cursor,
      end: cursor + text.length,
      highlightable: !SKIP_HIGHLIGHT_TAGS.has(parentTag),
    });
    cursor += text.length;
  }

  const appliedMarkerIds = new Set<string>();
  for (const entry of textNodes) {
    if (!entry.highlightable) {
      continue;
    }
    const text = entry.node.nodeValue ?? "";
    const overlaps = normalizedRanges.filter((range) => range.end > entry.start && range.start < entry.end);
    if (overlaps.length === 0) {
      continue;
    }

    const boundaries = new Set<number>([0, text.length]);
    for (const range of overlaps) {
      boundaries.add(Math.max(0, range.start - entry.start));
      boundaries.add(Math.min(text.length, range.end - entry.start));
    }
    const sortedBoundaries = [...boundaries].sort((left, right) => left - right);

    const fragment = document.createDocumentFragment();
    for (let index = 0; index < sortedBoundaries.length - 1; index += 1) {
      const segmentStart = sortedBoundaries[index];
      const segmentEnd = sortedBoundaries[index + 1];
      if (segmentStart === undefined || segmentEnd === undefined || segmentEnd <= segmentStart) {
        continue;
      }

      const globalStart = entry.start + segmentStart;
      const globalEnd = entry.start + segmentEnd;
      const coveringRange = overlaps.find((range) => range.start <= globalStart && range.end >= globalEnd);
      const segmentText = text.slice(segmentStart, segmentEnd);
      if (!coveringRange) {
        fragment.appendChild(document.createTextNode(segmentText));
        continue;
      }

      const mark = document.createElement("mark");
      mark.className = "workspace-reader__highlight";
      mark.setAttribute("data-highlight-id", coveringRange.id);
      if (!appliedMarkerIds.has(coveringRange.id)) {
        mark.id = coveringRange.id;
        appliedMarkerIds.add(coveringRange.id);
      }
      mark.textContent = segmentText;
      fragment.appendChild(mark);
    }

    entry.node.parentNode?.replaceChild(fragment, entry.node);
  }

  return { html: container.innerHTML, appliedMarkerIds };
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
    if (SKIP_HIGHLIGHT_TAGS.has(parentTag)) {
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
      const start = match.index;
      const end = start + match[0].length;
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

const highlightTextByRanges = (text: string, ranges: HighlightRange[]): ReactNode => {
  const normalized = normalizeRanges(ranges, text.length);
  if (normalized.length === 0) {
    return text;
  }

  const nodes: ReactNode[] = [];
  let cursor = 0;
  normalized.forEach((range, index) => {
    if (range.start > cursor) {
      nodes.push(text.slice(cursor, range.start));
    }
    nodes.push(
      <mark key={`reader-title-highlight-${range.id}-${index}`} className="workspace-reader__highlight">
        {text.slice(range.start, range.end)}
      </mark>
    );
    cursor = range.end;
  });
  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }
  return <>{nodes}</>;
};

const highlightTextByTerms = (text: string, terms: string[]): ReactNode => {
  const normalizedTerms = terms
    .map((term) => term.trim())
    .filter(Boolean)
    .sort((left, right) => right.length - left.length);
  if (normalizedTerms.length === 0) {
    return text;
  }

  const pattern = new RegExp(`(${normalizedTerms.map((term) => escapeRegExp(term)).join("|")})`, "gi");
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match = pattern.exec(text);
  while (match) {
    const start = match.index;
    const end = start + match[0].length;
    if (start > lastIndex) {
      nodes.push(text.slice(lastIndex, start));
    }
    nodes.push(
      <mark key={`reader-title-term-highlight-${start}-${end}`} className="workspace-reader__highlight">
        {text.slice(start, end)}
      </mark>
    );
    lastIndex = end;
    match = pattern.exec(text);
  }
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes.length === 0 ? text : <>{nodes}</>;
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
  let evidenceModel = EMPTY_EVIDENCE_MODEL;
  try {
    evidenceModel = createEvidenceModel(streamIds, streamNameById, streamMatchEvidence);
  } catch {
    evidenceModel = EMPTY_EVIDENCE_MODEL;
  }
  const hasHighlightCandidates =
    evidenceModel.ranges.length > 0 ||
    evidenceModel.terms.length > 0 ||
    evidenceModel.titleRanges.length > 0 ||
    evidenceModel.titleTerms.length > 0;
  const [showHighlights, setShowHighlights] = useState(true);

  let renderedContentHtml = contentHtml;
  let appliedMarkerIds = new Set<string>();
  if (showHighlights && contentHtml) {
    try {
      const offsetHighlightResult = highlightHtmlByOffsets(contentHtml, evidenceModel.ranges);
      renderedContentHtml = offsetHighlightResult.html;
      appliedMarkerIds = offsetHighlightResult.appliedMarkerIds;
      if (appliedMarkerIds.size === 0 && evidenceModel.terms.length > 0) {
        renderedContentHtml = highlightHtmlByTerms(contentHtml, evidenceModel.terms);
      }
    } catch {
      renderedContentHtml = contentHtml;
      appliedMarkerIds = new Set<string>();
    }
  }

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
      let summary: string | null = null;
      try {
        summary = buildEvidenceSummary(streamMatchReasons?.[streamId], streamMatchEvidence?.[streamId]);
      } catch {
        summary = null;
      }
      if (!summary) {
        return null;
      }
      return `${streamName}: ${summary}`;
    })
    .filter((value): value is string => Boolean(value));
  const matchedTermsSummary = buildMatchedTermsSummary(streamIds, streamMatchEvidence);
  const articleTitle = detail?.title || "Untitled article";
  let renderedArticleTitle: ReactNode = articleTitle;
  if (showHighlights) {
    renderedArticleTitle = highlightTextByRanges(articleTitle, evidenceModel.titleRanges);
    if (renderedArticleTitle === articleTitle && evidenceModel.titleTerms.length > 0) {
      renderedArticleTitle = highlightTextByTerms(articleTitle, evidenceModel.titleTerms);
    }
  }

  const jumpToHighlight = (markerId: string) => {
    const target = document.getElementById(markerId);
    if (!target) {
      return;
    }
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const toggleReadLabel = selectedArticle?.is_read ? "Mark as unread (m)" : "Mark as read (m)";
  const toggleSavedLabel = selectedArticle?.is_starred ? "Remove from saved (s)" : "Save article (s)";
  const openOriginalAvailable = Boolean(detail?.canonical_url);
  const openOriginalTooltip = openOriginalAvailable ? "Open original source (o)" : "Original source unavailable";
  const previousArticleLabel = "Previous article (k)";
  const nextArticleLabel = "Next article (j)";
  const toggleHighlightsLabel = showHighlights ? "Hide match highlights" : "Show match highlights";

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
                {renderedArticleTitle}
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
              {matchedTermsSummary ? (
                <Typography variant="body2" className="workspace-reader__match">
                  Matched terms: {matchedTermsSummary}
                </Typography>
              ) : null}
              {matchedEvidenceSummaries.length > 0 ? (
                <Typography variant="body2" className="workspace-reader__match">
                  Match evidence: {matchedEvidenceSummaries.join(" · ")}
                </Typography>
              ) : null}
            </Box>

            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap className="workspace-reader__actions">
              <Tooltip title={toggleReadLabel}>
                <span>
                  <IconButton
                    size="small"
                    aria-label={toggleReadLabel}
                    disabled={isMutating}
                    onClick={onToggleRead}
                    sx={{ width: 40, height: 40 }}
                  >
                    {selectedArticle?.is_read ? (
                      <MarkEmailUnreadRoundedIcon fontSize="small" />
                    ) : (
                      <DoneRoundedIcon fontSize="small" />
                    )}
                  </IconButton>
                </span>
              </Tooltip>
              <Tooltip title={toggleSavedLabel}>
                <span>
                  <IconButton
                    size="small"
                    aria-label={toggleSavedLabel}
                    disabled={isMutating}
                    onClick={onToggleSaved}
                    sx={{ width: 40, height: 40 }}
                  >
                    {selectedArticle?.is_starred ? (
                      <BookmarkRoundedIcon fontSize="small" />
                    ) : (
                      <BookmarkBorderRoundedIcon fontSize="small" />
                    )}
                  </IconButton>
                </span>
              </Tooltip>
              <Tooltip title={openOriginalTooltip}>
                <span>
                  <IconButton
                    size="small"
                    aria-label="Open original source (o)"
                    onClick={onOpenOriginal}
                    disabled={!openOriginalAvailable}
                    sx={{ width: 40, height: 40 }}
                  >
                    <OpenInNewRoundedIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
              <Tooltip title={previousArticleLabel}>
                <span>
                  <IconButton
                    size="small"
                    aria-label={previousArticleLabel}
                    onClick={() => onMoveSelection(-1)}
                    sx={{ width: 40, height: 40 }}
                  >
                    <NavigateBeforeRoundedIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
              <Tooltip title={nextArticleLabel}>
                <span>
                  <IconButton
                    size="small"
                    aria-label={nextArticleLabel}
                    onClick={() => onMoveSelection(1)}
                    sx={{ width: 40, height: 40 }}
                  >
                    <NavigateNextRoundedIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
              {hasHighlightCandidates ? (
                <Tooltip title={toggleHighlightsLabel}>
                  <span>
                    <IconButton
                      size="small"
                      aria-label={toggleHighlightsLabel}
                      onClick={() => setShowHighlights((current) => !current)}
                      sx={{ width: 40, height: 40 }}
                    >
                      {showHighlights ? (
                        <VisibilityOffRoundedIcon fontSize="small" />
                      ) : (
                        <VisibilityRoundedIcon fontSize="small" />
                      )}
                    </IconButton>
                  </span>
                </Tooltip>
              ) : null}
            </Stack>

            {evidenceModel.rows.length > 0 ? (
              <Box className="workspace-reader__evidence">
                <Typography variant="caption" className="workspace-reader__evidence-label">
                  Evidence details
                </Typography>
                <Stack spacing={0.75}>
                  {evidenceModel.rows.map((row) => {
                    const canJump = showHighlights && row.markerId && appliedMarkerIds.has(row.markerId);
                    return (
                      <Box key={row.id} className="workspace-reader__evidence-row">
                        <Typography variant="body2" className="workspace-reader__evidence-title">
                          {row.streamName}: {row.title}
                        </Typography>
                        {row.snippet ? (
                          <Typography variant="caption" className="workspace-reader__evidence-snippet">
                            {row.snippet}
                          </Typography>
                        ) : null}
                        {canJump ? (
                          <Button
                            size="small"
                            variant="text"
                            className="workspace-reader__evidence-jump"
                            onClick={() => jumpToHighlight(row.markerId!)}
                          >
                            Jump to highlight
                          </Button>
                        ) : null}
                      </Box>
                    );
                  })}
                </Stack>
              </Box>
            ) : null}
          </Box>

          <Divider />

          {renderedContentHtml ? (
            <Box className="workspace-reader__body" dangerouslySetInnerHTML={{ __html: renderedContentHtml }} />
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
