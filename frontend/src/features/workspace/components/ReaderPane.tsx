import { Alert, Box, Button, Divider, Paper, Stack, Typography } from "@mui/material";

import { formatRelativeTime } from "../lib/time";
import type { ArticleDetail, ArticleListItem } from "../../../shared/types/contracts";

type ReaderPaneProps = {
  selectedArticle: ArticleListItem | undefined;
  selectedArticleId: string;
  detail: ArticleDetail | undefined;
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

export function ReaderPane({
  selectedArticle,
  selectedArticleId,
  detail,
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
          </Box>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
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
          </Stack>

          <Divider />

          <Typography variant="body1" className="workspace-reader__body">
            {detail.content_text || "No content available."}
          </Typography>
        </Stack>
      ) : null}
    </Paper>
  );
}
