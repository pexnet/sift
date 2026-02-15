import { List, ListItem, ListItemButton, ListItemText, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import type { RefObject } from "react";

import { AsyncState } from "../../../shared/ui/AsyncState";
import type { ArticleListItem, WorkspaceSearch } from "../../../shared/types/contracts";

type ArticlesPaneProps = {
  density: "compact" | "comfortable";
  search: WorkspaceSearch;
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
  density,
  search,
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
    <Paper className="react-pane" component="section" elevation={0}>
      <Typography variant="h6" gutterBottom>
        Articles
      </Typography>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 1, flexWrap: "wrap" }}>
        <TextField
          size="small"
          label="Search"
          value={search.q}
          inputRef={searchInputRef}
          onChange={(event) => onSearchChange(event.target.value)}
        />
        <TextField
          size="small"
          select
          label="State"
          value={search.state}
          onChange={(event) => onStateChange(event.target.value as WorkspaceSearch["state"])}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="all">All</MenuItem>
          <MenuItem value="unread">Unread</MenuItem>
          <MenuItem value="saved">Saved</MenuItem>
          <MenuItem value="archived">Archived</MenuItem>
          <MenuItem value="fresh">Fresh</MenuItem>
          <MenuItem value="recent">Recent</MenuItem>
        </TextField>
      </Stack>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        empty={articleItems.length === 0}
        loadingLabel="Loading articles..."
        errorLabel="Failed to load articles."
        emptyLabel="No articles found."
      />

      {!isLoading && !isError ? (
        <List dense={density === "compact"}>
          {articleItems.map((article) => (
            <ListItem key={article.id} disablePadding>
              <ListItemButton selected={selectedArticleId === article.id} onClick={() => onArticleSelect(article.id)}>
                <ListItemText
                  primary={article.title || "Untitled article"}
                  secondary={article.feed_title ?? ""}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      ) : null}
    </Paper>
  );
}
