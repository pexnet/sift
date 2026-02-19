import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";

import type { FeedHealthLifecycleFilter } from "../../../shared/types/contracts";
import { useFeedHealthQuery, useUpdateFeedLifecycleMutation, useUpdateFeedSettingsMutation } from "../api/feedHealthHooks";

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
  const [intervalByFeedId, setIntervalByFeedId] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const healthQuery = useFeedHealthQuery({
    lifecycle,
    q: query,
    stale_only: staleOnly,
    error_only: errorOnly,
    limit: 50,
    offset: 0,
  });
  const updateSettingsMutation = useUpdateFeedSettingsMutation();
  const lifecycleMutation = useUpdateFeedLifecycleMutation();

  const items = healthQuery.data?.items;
  const summary = healthQuery.data?.summary;

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
    <Paper component="section" className="panel settings-panel" sx={{ maxWidth: 1200, mx: "auto" }} aria-labelledby="feed-health-heading">
      <Stack spacing={2}>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ xs: "stretch", sm: "center" }} spacing={1}>
          <Typography id="feed-health-heading" variant="h4" component="h1">
            Feed health
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <Button component="a" href="/account" size="small" variant="outlined">
              Back to settings
            </Button>
          </Stack>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Inspect feed freshness and failures, then manage lifecycle and fetch interval.
        </Typography>

        {feedback ? <Alert severity={feedback.severity}>{feedback.message}</Alert> : null}
        {healthQuery.isError ? <Alert severity="error">Failed to load feed health.</Alert> : null}

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
            label="Search"
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
          <Button variant="outlined" onClick={onApplySearch}>
            Apply
          </Button>
        </Stack>

        {summary ? (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={`Total ${summary.total_feed_count}`} size="small" />
            <Chip label={`Active ${summary.active_feed_count}`} size="small" />
            <Chip label={`Paused ${summary.paused_feed_count}`} size="small" />
            <Chip label={`Archived ${summary.archived_feed_count}`} size="small" />
            <Chip label={`Stale ${summary.stale_feed_count}`} size="small" />
            <Chip label={`Errors ${summary.error_feed_count}`} size="small" />
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

        <Stack spacing={1.2}>
          {(items ?? []).map((item) => (
            <Box
              key={item.feed_id}
              sx={{
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 1,
                p: 1.5,
              }}
            >
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} justifyContent="space-between">
                <Box sx={{ minWidth: 0 }}>
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <Typography variant="h6" component="h2">
                      {item.title}
                    </Typography>
                    <Chip label={item.lifecycle_status} size="small" />
                    {item.is_stale ? <Chip label="stale" color="warning" size="small" /> : null}
                    {item.last_fetch_error ? <Chip label="error" color="error" size="small" /> : null}
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ wordBreak: "break-all" }}>
                    {item.url}
                  </Typography>
                  <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap sx={{ mt: 0.8 }}>
                    <Typography variant="caption">Unread: {item.unread_count}</Typography>
                    <Typography variant="caption">Articles (7d): {item.articles_last_7d}</Typography>
                    <Typography variant="caption">Cadence: {formatPerDay(item.estimated_articles_per_day_7d)}</Typography>
                    <Typography variant="caption">Last success: {formatDateTime(item.last_fetch_success_at)}</Typography>
                    <Typography variant="caption">Last error: {formatDateTime(item.last_fetch_error_at)}</Typography>
                  </Stack>
                  {item.last_fetch_error ? (
                    <Typography variant="caption" color="error" sx={{ display: "block", mt: 0.6 }}>
                      {item.last_fetch_error}
                    </Typography>
                  ) : null}
                </Box>

                <Stack spacing={1} sx={{ minWidth: { xs: "100%", md: 260 } }}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <TextField
                      size="small"
                      label="Fetch interval (minutes)"
                      value={intervalValueByFeedId[item.feed_id] ?? ""}
                      onChange={(event) =>
                        setIntervalByFeedId((previous) => ({
                          ...previous,
                          [item.feed_id]: event.target.value,
                        }))
                      }
                      type="number"
                      slotProps={{ htmlInput: { min: 1, max: 10080 } }}
                      fullWidth
                    />
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={isMutating}
                      onClick={() => void updateInterval(item.feed_id)}
                    >
                      Save
                    </Button>
                  </Stack>

                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {item.lifecycle_status === "active" ? (
                      <Button
                        size="small"
                        variant="outlined"
                        disabled={isMutating}
                        onClick={() => void updateLifecycle(item.feed_id, "pause")}
                      >
                        Pause
                      </Button>
                    ) : null}
                    {item.lifecycle_status === "paused" ? (
                      <Button
                        size="small"
                        variant="outlined"
                        disabled={isMutating}
                        onClick={() => void updateLifecycle(item.feed_id, "resume")}
                      >
                        Resume
                      </Button>
                    ) : null}
                    {item.lifecycle_status === "archived" ? (
                      <Button
                        size="small"
                        variant="outlined"
                        disabled={isMutating}
                        onClick={() => void updateLifecycle(item.feed_id, "unarchive")}
                      >
                        Unarchive
                      </Button>
                    ) : (
                      <Button
                        size="small"
                        color="warning"
                        variant="outlined"
                        disabled={isMutating}
                        onClick={() => void updateLifecycle(item.feed_id, "archive")}
                      >
                        Archive
                      </Button>
                    )}
                  </Stack>
                </Stack>
              </Stack>
            </Box>
          ))}
        </Stack>
      </Stack>
    </Paper>
  );
}
