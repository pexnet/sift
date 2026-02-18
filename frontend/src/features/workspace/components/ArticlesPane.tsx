import DoneAllRoundedIcon from "@mui/icons-material/DoneAllRounded";
import { Alert, IconButton, MenuItem, Paper, Stack, TextField, Tooltip, Typography } from "@mui/material";
import type { RefObject } from "react";

import { formatRelativeTime } from "../lib/time";
import { buildMatchedTermsSummary } from "../lib/matchEvidence";
import type { ArticleListItem, WorkspaceSearch } from "../../../shared/types/contracts";

type ArticlesPaneProps = {
  density: "compact" | "comfortable";
  search: WorkspaceSearch;
  scopeLabel: string;
  streamNameById: Record<string, string>;
  articleItems: ArticleListItem[];
  articleTotal: number;
  selectedArticleId: string;
  isLoading: boolean;
  isError: boolean;
  searchInputRef: RefObject<HTMLInputElement | null>;
  isMarkAllReadPending: boolean;
  onSearchChange: (value: string) => void;
  onStateChange: (state: WorkspaceSearch["state"]) => void;
  onArticleSelect: (articleId: string) => void;
  onMarkScopeRead: () => void;
};

export function ArticlesPane({
  search,
  scopeLabel,
  streamNameById,
  articleItems,
  articleTotal,
  selectedArticleId,
  isLoading,
  isError,
  searchInputRef,
  isMarkAllReadPending,
  onSearchChange,
  onStateChange,
  onArticleSelect,
  onMarkScopeRead,
}: ArticlesPaneProps) {
  const formatMatchedStreams = (streamIds: string[]): string | null => {
    const names = streamIds
      .map((streamId) => streamNameById[streamId])
      .filter((name): name is string => Boolean(name));
    if (names.length === 0) {
      return null;
    }
    if (names.length <= 2) {
      return names.join(", ");
    }
    return `${names[0]}, ${names[1]} +${names.length - 2}`;
  };

  const primaryMatchReason = (
    streamIds: string[],
    streamMatchReasons: Record<string, string> | null | undefined
  ): string | null => {
    if (!streamMatchReasons) {
      return null;
    }
    for (const streamId of streamIds) {
      const reason = streamMatchReasons[streamId];
      if (reason) {
        const streamName = streamNameById[streamId] || "monitoring stream";
        return `${streamName}: ${reason}`;
      }
    }
    return null;
  };

  const markScopeReadTooltip = isMarkAllReadPending
    ? "Marking all articles in current scope as read"
    : "Mark all articles in current scope as read";
  const markScopeReadAriaLabel = isMarkAllReadPending
    ? "Marking all articles in current scope as read"
    : "Mark all articles in current scope as read";

  return (
    <Paper className="workspace-list" component="section" elevation={0}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }} className="workspace-list__header">
        <Typography variant="h4" className="workspace-list__title">
          {scopeLabel}
        </Typography>
        <Stack direction="row" spacing={1}>
          <TextField
            size="small"
            select
            label="State"
            value={search.state}
            onChange={(event) => onStateChange(event.target.value as WorkspaceSearch["state"])}
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="unread">Unread</MenuItem>
            <MenuItem value="saved">Saved</MenuItem>
            <MenuItem value="archived">Archived</MenuItem>
            <MenuItem value="fresh">Fresh</MenuItem>
            <MenuItem value="recent">Recent</MenuItem>
          </TextField>
        </Stack>
      </Stack>

      <Stack direction="row" spacing={1} sx={{ mb: 1.5 }} className="workspace-list__controls">
        <TextField
          size="small"
          label="Search"
          value={search.q}
          inputRef={searchInputRef}
          onChange={(event) => onSearchChange(event.target.value)}
          sx={{ flex: 1 }}
        />
        <Tooltip title={markScopeReadTooltip}>
          <span>
            <IconButton
              size="small"
              aria-label={markScopeReadAriaLabel}
              onClick={onMarkScopeRead}
              disabled={isLoading || isMarkAllReadPending || articleTotal === 0}
              sx={{ width: 40, height: 40 }}
            >
              <DoneAllRoundedIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </Stack>

      {isLoading ? <Typography color="text.secondary">Loading articles...</Typography> : null}
      {isError ? <Alert severity="error">Failed to load articles.</Alert> : null}
      {!isLoading && !isError && articleItems.length === 0 ? (
        <Typography color="text.secondary">No articles found.</Typography>
      ) : null}

      {!isLoading && !isError ? (
        <Stack className="workspace-list__rows" spacing={0}>
          {articleItems.map((article) => {
            const selected = selectedArticleId === article.id;
            const unread = !article.is_read;
            const saved = article.is_starred;
            const relativePublished = article.published_at ? formatRelativeTime(article.published_at) : "";
            const matchedStreams = formatMatchedStreams(article.stream_ids ?? []);
            const matchedReason = primaryMatchReason(article.stream_ids ?? [], article.stream_match_reasons);
            const matchedTerms = buildMatchedTermsSummary(article.stream_ids ?? [], article.stream_match_evidence);
            const rowClassName = [
              "workspace-row",
              selected ? "workspace-row--selected" : "",
              unread ? "" : "workspace-row--read",
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <button
                key={article.id}
                type="button"
                className={rowClassName}
                onClick={() => onArticleSelect(article.id)}
                aria-label={article.title || "Untitled article"}
              >
                <span className={unread ? "workspace-row__dot workspace-row__dot--unread" : "workspace-row__dot"} />
                <span className={saved ? "workspace-row__saved workspace-row__saved--active" : "workspace-row__saved"}>
                  {saved ? "★" : "☆"}
                </span>
                <span className="workspace-row__content">
                  <span className="workspace-row__title">{article.title || "Untitled article"}</span>
                  <span className="workspace-row__meta">{article.feed_title ?? "Unknown source"}</span>
                  {matchedStreams ? (
                    <span className="workspace-row__match">Matched: {matchedStreams}</span>
                  ) : null}
                  {matchedReason ? (
                    <span className="workspace-row__match">Why matched: {matchedReason}</span>
                  ) : null}
                  {matchedTerms ? (
                    <span className="workspace-row__match">Matched terms: {matchedTerms}</span>
                  ) : null}
                </span>
                <span className="workspace-row__time">{relativePublished}</span>
              </button>
            );
          })}
        </Stack>
      ) : null}
    </Paper>
  );
}
