import { Alert, Box, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import type { RefObject } from "react";

import { formatRelativeTime } from "../lib/time";
import type { ArticleListItem, WorkspaceSearch } from "../../../shared/types/contracts";

type ArticlesPaneProps = {
  density: "compact" | "comfortable";
  search: WorkspaceSearch;
  scopeLabel: string;
  articleItems: ArticleListItem[];
  selectedArticleId: string;
  isLoading: boolean;
  isError: boolean;
  searchInputRef: RefObject<HTMLInputElement | null>;
  onSearchChange: (value: string) => void;
  onStateChange: (state: WorkspaceSearch["state"]) => void;
  onArticleSelect: (articleId: string) => void;
};

export function ArticlesPane({
  search,
  scopeLabel,
  articleItems,
  selectedArticleId,
  isLoading,
  isError,
  searchInputRef,
  onSearchChange,
  onStateChange,
  onArticleSelect,
}: ArticlesPaneProps) {
  return (
    <Paper className="workspace-list" component="section" elevation={0}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography variant="h4" className="workspace-list__title">
          {scopeLabel}
        </Typography>
      </Stack>

      <Stack direction="row" spacing={1} sx={{ mb: 1.5 }}>
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
        <TextField
          size="small"
          label="Search"
          value={search.q}
          inputRef={searchInputRef}
          onChange={(event) => onSearchChange(event.target.value)}
          sx={{ flex: 1 }}
        />
      </Stack>

      <Box className="workspace-list__banner" role="note">
        <Typography variant="body2">
          When using the "Magic" sorting option, only articles from the past 30 days are displayed.
        </Typography>
      </Box>

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

            return (
              <button
                key={article.id}
                type="button"
                className={selected ? "workspace-row workspace-row--selected" : "workspace-row"}
                onClick={() => onArticleSelect(article.id)}
              >
                <span className={unread ? "workspace-row__dot workspace-row__dot--unread" : "workspace-row__dot"} />
                <span className={saved ? "workspace-row__saved workspace-row__saved--active" : "workspace-row__saved"}>
                  {saved ? "★" : "☆"}
                </span>
                <span className="workspace-row__content">
                  <span className="workspace-row__title">{article.title || "Untitled article"}</span>
                  <span className="workspace-row__meta">
                    {article.feed_title ?? "Unknown source"}
                    {article.published_at ? ` · ${formatRelativeTime(article.published_at)}` : ""}
                  </span>
                </span>
              </button>
            );
          })}
        </Stack>
      ) : null}
    </Paper>
  );
}
