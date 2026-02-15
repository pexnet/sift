import { Alert, Box, Button, Chip, Divider, Paper, Stack, Typography } from "@mui/material";

import { AsyncState } from "../../../shared/ui/AsyncState";
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
}: ReaderPaneProps) {
  return (
    <Paper className="react-pane" component="section" elevation={0}>
      <Typography variant="h6" gutterBottom>
        Reader
      </Typography>

      {selectedArticle ? (
        <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
          <Button size="small" variant="outlined" disabled={isMutating} onClick={onToggleRead}>
            {selectedArticle.is_read ? "Mark unread" : "Mark read"}
          </Button>
          <Button size="small" variant="outlined" disabled={isMutating} onClick={onToggleSaved}>
            {selectedArticle.is_starred ? "Unsave" : "Save"}
          </Button>
          {selectedArticle.is_archived ? <Chip size="small" label="Archived" /> : null}
        </Stack>
      ) : null}

      {hasMutationError ? <Alert severity="error">Failed to update article state.</Alert> : null}

      {!selectedArticleId ? (
        <Typography variant="body2" color="text.secondary">
          Select an article to load reader content.
        </Typography>
      ) : (
        <AsyncState
          isLoading={isLoading}
          isError={isError}
          empty={!detail}
          loadingLabel="Loading article..."
          errorLabel="Failed to load article details."
          emptyLabel="No article content available."
        />
      )}

      {detail ? (
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6">{detail.title || "Untitled article"}</Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {detail.feed_title || ""}
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {detail.content_text || "No content available."}
          </Typography>
        </Box>
      ) : null}
    </Paper>
  );
}
