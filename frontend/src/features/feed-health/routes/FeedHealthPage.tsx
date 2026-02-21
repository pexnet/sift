import AddLinkRoundedIcon from "@mui/icons-material/AddLinkRounded";
import ArchiveRoundedIcon from "@mui/icons-material/ArchiveRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import PauseCircleRoundedIcon from "@mui/icons-material/PauseCircleRounded";
import PlayCircleRoundedIcon from "@mui/icons-material/PlayCircleRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import UnarchiveRoundedIcon from "@mui/icons-material/UnarchiveRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";

import { useFoldersQuery } from "../../workspace/api/workspaceHooks";
import { SettingsLayout } from "../../settings/components/SettingsLayout";
import type { FeedHealthItem, FeedHealthLifecycleFilter } from "../../../shared/types/contracts";
import {
  useCreateFeedMutation,
  useFeedHealthQuery,
  useUpdateFeedLifecycleMutation,
  useUpdateFeedSettingsMutation,
} from "../api/feedHealthHooks";

type Feedback = {
  severity: "success" | "error";
  message: string;
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Never";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function formatPerDay(value: number): string {
  return `${value.toFixed(2)}/day`;
}

export function FeedHealthPage() {
  const [lifecycle, setLifecycle] = useState<FeedHealthLifecycleFilter>("all");
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [staleOnly, setStaleOnly] = useState(false);
  const [errorOnly, setErrorOnly] = useState(false);
  const [selectedFeed, setSelectedFeed] = useState<FeedHealthItem | null>(null);
  const [intervalByFeedId, setIntervalByFeedId] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createUrl, setCreateUrl] = useState("");
  const [createTitle, setCreateTitle] = useState("");
  const [createFolderId, setCreateFolderId] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const foldersQuery = useFoldersQuery();
  const healthQuery = useFeedHealthQuery({
    lifecycle,
    q: query,
    stale_only: staleOnly,
    error_only: errorOnly,
    all: true,
    limit: 200,
    offset: 0,
  });
  const updateSettingsMutation = useUpdateFeedSettingsMutation();
  const lifecycleMutation = useUpdateFeedLifecycleMutation();
  const createFeedMutation = useCreateFeedMutation();

  const items = healthQuery.data?.items;
  const summary = healthQuery.data?.summary;
  const folderNameById = useMemo(
    () => new Map((foldersQuery.data ?? []).map((folder) => [folder.id, folder.name] as const)),
    [foldersQuery.data]
  );

  const isLoading = healthQuery.isLoading;
  const isMutating = updateSettingsMutation.isPending || lifecycleMutation.isPending;
  const intervalValueByFeedId = useMemo(() => {
    const values = { ...intervalByFeedId };
    for (const item of items ?? []) {
      if (!values[item.feed_id]) {
        values[item.feed_id] = String(item.fetch_interval_minutes);
      }
    }
    return values;
  }, [intervalByFeedId, items]);

  const onApplySearch = () => {
    setQuery(queryInput.trim());
  };

  const resetFilters = () => {
    setLifecycle("all");
    setQueryInput("");
    setQuery("");
    setStaleOnly(false);
    setErrorOnly(false);
  };

  const closeCreateDialog = () => {
    setCreateOpen(false);
    setCreateUrl("");
    setCreateTitle("");
    setCreateFolderId("");
    setCreateError(null);
  };

  const submitCreateFeed = async () => {
    setCreateError(null);
    setFeedback(null);

    const url = createUrl.trim();
    if (!url) {
      setCreateError("Feed URL is required.");
      return;
    }
    try {
      new URL(url);
    } catch {
      setCreateError("Feed URL must be a valid URL.");
      return;
    }

    try {
      await createFeedMutation.mutateAsync({
        title: createTitle.trim() || url,
        url,
        folder_id: createFolderId.length > 0 ? createFolderId : null,
      });
      closeCreateDialog();
      setFeedback({ severity: "success", message: "Feed created." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create feed.";
      setCreateError(message);
    }
  };

  const updateInterval = async (feedId: string) => {
    setFeedback(null);
    const raw = intervalValueByFeedId[feedId] ?? "";
    const value = Number(raw);
    if (!Number.isFinite(value)) {
      setFeedback({ severity: "error", message: "Fetch interval must be a number." });
      return;
    }
    try {
      await updateSettingsMutation.mutateAsync({
        feedId,
        payload: { fetch_interval_minutes: Math.round(value) },
      });
      setFeedback({ severity: "success", message: "Feed settings updated." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update feed settings.";
      setFeedback({ severity: "error", message });
    }
  };

  const updateLifecycle = async (
    feedId: string,
    action: "pause" | "resume" | "archive" | "unarchive",
  ) => {
    setFeedback(null);
    if (action === "archive") {
      const confirmed = window.confirm(
        "Archive this feed? Existing unread articles from this feed will be marked as read."
      );
      if (!confirmed) {
        return;
      }
    }
    try {
      const result = await lifecycleMutation.mutateAsync({
        feedId,
        payload: { action },
      });
      if (action === "archive") {
        setFeedback({
          severity: "success",
          message: `Feed archived. Marked ${result.marked_read_count} unread article(s) as read.`,
        });
        return;
      }
      setFeedback({ severity: "success", message: "Feed lifecycle updated." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update feed lifecycle.";
      setFeedback({ severity: "error", message });
    }
  };

  return (
    <SettingsLayout
      activeSection="feed-health"
      title="Feed health"
      headingId="feed-health-heading"
      maxWidth={1300}
      description="Review freshness and ingest failures, then adjust lifecycle state and polling cadence per feed."
      actions={
        <Button size="small" variant="contained" startIcon={<AddLinkRoundedIcon />} onClick={() => setCreateOpen(true)}>
          Add feed
        </Button>
      }
    >
      {healthQuery.data?.last_updated_at ? (
        <Typography variant="caption" color="text.secondary">
          Last refreshed: {formatDateTime(healthQuery.data.last_updated_at)}
        </Typography>
      ) : null}

      {feedback ? <Alert severity={feedback.severity}>{feedback.message}</Alert> : null}
      {healthQuery.isError ? <Alert severity="error">Failed to load feed health.</Alert> : null}

      <Box sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 1.5 }}>
        <Stack spacing={1.2}>
          <Typography variant="subtitle2">Filters</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="feed-health-lifecycle-label">Lifecycle</InputLabel>
              <Select
                labelId="feed-health-lifecycle-label"
                label="Lifecycle"
                value={lifecycle}
                onChange={(event) => setLifecycle(event.target.value as FeedHealthLifecycleFilter)}
              >
                <MenuItem value="all">All</MenuItem>
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="paused">Paused</MenuItem>
                <MenuItem value="archived">Archived</MenuItem>
              </Select>
            </FormControl>

            <FormControlLabel
              control={<Switch checked={staleOnly} onChange={(event) => setStaleOnly(event.target.checked)} />}
              label="Stale only"
            />
            <FormControlLabel
              control={<Switch checked={errorOnly} onChange={(event) => setErrorOnly(event.target.checked)} />}
              label="Error only"
            />

            <TextField
              size="small"
              label="Title or URL"
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  onApplySearch();
                }
              }}
              sx={{ flex: 1, minWidth: 220 }}
            />
            <Stack direction="row" spacing={1}>
              <Button variant="outlined" onClick={onApplySearch}>
                Apply filters
              </Button>
              <Button variant="text" onClick={resetFilters}>
                Reset
              </Button>
            </Stack>
          </Stack>
        </Stack>
      </Box>

      {summary ? (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip label={`Total ${summary.total_feed_count}`} size="small" />
          <Chip label={`Active ${summary.active_feed_count}`} size="small" />
          <Chip label={`Paused ${summary.paused_feed_count}`} size="small" />
          <Chip label={`Archived ${summary.archived_feed_count}`} size="small" />
          <Chip label={`Stale ${summary.stale_feed_count}`} size="small" color="warning" />
          <Chip label={`Errors ${summary.error_feed_count}`} size="small" color="error" />
        </Stack>
      ) : null}

      {isLoading ? (
        <Box sx={{ py: 3, display: "flex", justifyContent: "center" }}>
          <CircularProgress size={24} />
        </Box>
      ) : null}

      {!isLoading && (items ?? []).length === 0 ? (
        <Alert severity="info">No feeds matched the selected filters.</Alert>
      ) : null}

      <Paper variant="outlined" sx={{ p: 1.1 }}>
        <Stack spacing={0.45}>
          <Stack
            direction="row"
            alignItems="center"
            spacing={1}
            sx={{ px: 1, py: 0.7, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <Typography variant="caption" sx={{ flex: 2, fontWeight: 700 }}>
              Feed
            </Typography>
            <Typography variant="caption" sx={{ flex: 1.1, fontWeight: 700 }}>
              Health
            </Typography>
            <Typography variant="caption" sx={{ width: 72, fontWeight: 700 }}>
              Unread
            </Typography>
            <Typography variant="caption" sx={{ width: 92, fontWeight: 700 }}>
              7d cadence
            </Typography>
            <Typography variant="caption" sx={{ width: 152, fontWeight: 700 }}>
              Last success
            </Typography>
            <Typography variant="caption" sx={{ width: 152, fontWeight: 700 }}>
              Last error
            </Typography>
            <Typography variant="caption" sx={{ width: 138, fontWeight: 700 }}>
              Interval
            </Typography>
            <Typography variant="caption" sx={{ width: 136, fontWeight: 700, textAlign: "right" }}>
              Actions
            </Typography>
          </Stack>

          {(items ?? []).map((item) => (
            <Stack key={item.feed_id} direction="row" alignItems="center" spacing={1} sx={{ px: 1, py: 0.6 }}>
              <Box sx={{ flex: 2, minWidth: 0 }}>
                <Button
                  size="small"
                  variant="text"
                  sx={{
                    px: 0,
                    justifyContent: "flex-start",
                    alignItems: "flex-start",
                    minWidth: 0,
                    width: "100%",
                    textTransform: "none",
                    fontWeight: 600,
                  }}
                  aria-label={`Open details for ${item.title}`}
                  onClick={() => setSelectedFeed(item)}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      whiteSpace: "normal",
                      wordBreak: "break-word",
                      lineHeight: 1.25,
                    }}
                  >
                    {item.title}
                  </Typography>
                </Button>
              </Box>

              <Stack direction="row" spacing={0.4} sx={{ flex: 1.1 }}>
                <Tooltip title={item.lifecycle_status}>
                  {item.lifecycle_status === "active" ? (
                    <CheckCircleRoundedIcon color="success" fontSize="small" />
                  ) : item.lifecycle_status === "paused" ? (
                    <PauseCircleRoundedIcon color="warning" fontSize="small" />
                  ) : (
                    <ArchiveRoundedIcon color="disabled" fontSize="small" />
                  )}
                </Tooltip>
                {item.is_stale ? (
                  <Tooltip title={item.stale_age_hours !== null ? `Stale ${item.stale_age_hours.toFixed(1)}h` : "Stale"}>
                    <WarningAmberRoundedIcon color="warning" fontSize="small" />
                  </Tooltip>
                ) : null}
                {item.last_fetch_error ? (
                  <Tooltip title={item.last_fetch_error}>
                    <ErrorOutlineRoundedIcon color="error" fontSize="small" />
                  </Tooltip>
                ) : null}
              </Stack>

              <Typography variant="body2" sx={{ width: 72 }}>
                {item.unread_count}
              </Typography>
              <Typography variant="body2" sx={{ width: 92 }}>
                {formatPerDay(item.estimated_articles_per_day_7d)}
              </Typography>
              <Typography variant="caption" sx={{ width: 152 }} noWrap>
                {formatDateTime(item.last_fetch_success_at)}
              </Typography>
              <Typography variant="caption" sx={{ width: 152 }} noWrap>
                {formatDateTime(item.last_fetch_error_at)}
              </Typography>

              <Stack direction="row" spacing={0.5} sx={{ width: 138 }}>
                <TextField
                  size="small"
                  value={intervalValueByFeedId[item.feed_id] ?? ""}
                  onChange={(event) =>
                    setIntervalByFeedId((previous) => ({
                      ...previous,
                      [item.feed_id]: event.target.value,
                    }))
                  }
                  type="number"
                  slotProps={{ htmlInput: { min: 1, max: 10080, "aria-label": "Fetch interval (minutes)" } }}
                  sx={{ width: 76 }}
                />
                <Tooltip title="Save interval">
                  <span>
                    <IconButton
                      size="small"
                      aria-label={`Save interval for ${item.title}`}
                      disabled={isMutating}
                      onClick={() => void updateInterval(item.feed_id)}
                    >
                      <SaveRoundedIcon fontSize="small" />
                    </IconButton>
                  </span>
                </Tooltip>
              </Stack>

              <Stack direction="row" spacing={0.1} sx={{ width: 136, justifyContent: "flex-end" }}>
                {item.lifecycle_status === "active" ? (
                  <Tooltip title="Pause updates">
                    <span>
                      <IconButton
                        size="small"
                        aria-label={`Pause updates for ${item.title}`}
                        disabled={isMutating}
                        onClick={() => void updateLifecycle(item.feed_id, "pause")}
                      >
                        <PauseCircleRoundedIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                ) : null}
                {item.lifecycle_status === "paused" ? (
                  <Tooltip title="Resume updates">
                    <span>
                      <IconButton
                        size="small"
                        aria-label={`Resume updates for ${item.title}`}
                        disabled={isMutating}
                        onClick={() => void updateLifecycle(item.feed_id, "resume")}
                      >
                        <PlayCircleRoundedIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                ) : null}
                {item.lifecycle_status === "archived" ? (
                  <Tooltip title="Unarchive feed">
                    <span>
                      <IconButton
                        size="small"
                        aria-label={`Unarchive ${item.title}`}
                        disabled={isMutating}
                        onClick={() => void updateLifecycle(item.feed_id, "unarchive")}
                      >
                        <UnarchiveRoundedIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                ) : (
                  <Tooltip title="Archive feed">
                    <span>
                      <IconButton
                        size="small"
                        aria-label={`Archive ${item.title}`}
                        disabled={isMutating}
                        onClick={() => void updateLifecycle(item.feed_id, "archive")}
                      >
                        <ArchiveRoundedIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                )}
              </Stack>
            </Stack>
          ))}
        </Stack>
      </Paper>

      <Dialog open={selectedFeed !== null} onClose={() => setSelectedFeed(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedFeed?.title ?? "Feed details"}</DialogTitle>
        <DialogContent>
          {selectedFeed ? (
            <Stack spacing={1.1}>
              <Typography variant="body2">
                URL: {selectedFeed.url}
              </Typography>
              <Typography variant="body2">
                Website: {selectedFeed.site_url ?? "Unknown"}
              </Typography>
              <Typography variant="body2">
                Lifecycle: {selectedFeed.lifecycle_status}
              </Typography>
              <Typography variant="body2">
                Folder:{" "}
                {selectedFeed.folder_id ? (folderNameById.get(selectedFeed.folder_id) ?? "Folder") : "Unfiled"}
              </Typography>
              <Typography variant="body2">
                Interval: {selectedFeed.fetch_interval_minutes} minutes
              </Typography>
              <Typography variant="body2">
                Last fetched: {formatDateTime(selectedFeed.last_fetched_at)}
              </Typography>
              <Typography variant="body2">
                Last success: {formatDateTime(selectedFeed.last_fetch_success_at)}
              </Typography>
              <Typography variant="body2">
                Last error time: {formatDateTime(selectedFeed.last_fetch_error_at)}
              </Typography>
              <Typography variant="body2" color={selectedFeed.last_fetch_error ? "error.main" : "text.secondary"}>
                Last error: {selectedFeed.last_fetch_error ?? "None"}
              </Typography>
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedFeed(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={createOpen} onClose={closeCreateDialog}>
        <DialogTitle>Add feed</DialogTitle>
        <DialogContent>
          <Stack spacing={1.2} sx={{ mt: 0.4, minWidth: { xs: 280, sm: 420 } }}>
            {createError ? <Alert severity="error">{createError}</Alert> : null}
            <TextField
              label="Feed URL"
              value={createUrl}
              onChange={(event) => setCreateUrl(event.target.value)}
              placeholder="https://example.com/rss"
              autoFocus
              required
              size="small"
            />
            <TextField
              label="Title (optional)"
              value={createTitle}
              onChange={(event) => setCreateTitle(event.target.value)}
              size="small"
            />
            <FormControl size="small">
              <InputLabel id="create-feed-folder-label">Folder</InputLabel>
              <Select
                labelId="create-feed-folder-label"
                label="Folder"
                value={createFolderId}
                onChange={(event) => setCreateFolderId(event.target.value)}
              >
                <MenuItem value="">Unfiled</MenuItem>
                {(foldersQuery.data ?? []).map((folder) => (
                  <MenuItem key={folder.id} value={folder.id}>
                    {folder.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeCreateDialog}>Cancel</Button>
          <Button variant="contained" onClick={() => void submitCreateFeed()} disabled={createFeedMutation.isPending}>
            Add feed
          </Button>
        </DialogActions>
      </Dialog>
    </SettingsLayout>
  );
}
