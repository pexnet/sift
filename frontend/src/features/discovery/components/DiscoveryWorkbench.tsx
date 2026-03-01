import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import {
  Alert,
  Box,
  Button,
  Chip,
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
import { useMemo, useState, type FormEvent } from "react";

import type { RecommendationFilters } from "../../../shared/api/discoveryApi";
import type { DiscoveryStream, FeedRecommendation } from "../../../shared/types/contracts";
import {
  useCreateDiscoveryStreamMutation,
  useDecideFeedRecommendationMutation,
  useDeleteDiscoveryStreamMutation,
  useDiscoveryStreamsQuery,
  useFeedRecommendationsQuery,
  useFeedRecommendationSummaryQuery,
  useGenerateDiscoveryStreamMutation,
  useResetFeedRecommendationMutation,
  useUpdateDiscoveryStreamMutation,
} from "../api/discoveryHooks";

type DiscoveryWorkbenchProps = {
  mode: "settings" | "workspace";
};

type RecommendationStatusFilter = "all" | "pending" | "accepted" | "denied" | "resolved_existing";

type Feedback = {
  severity: "success" | "error" | "info";
  message: string;
};

type DiscoveryFormState = {
  name: string;
  matchQuery: string;
  includeKeywords: string;
  excludeKeywords: string;
  isActive: boolean;
};

const DEFAULT_FORM_STATE: DiscoveryFormState = {
  name: "",
  matchQuery: "",
  includeKeywords: "",
  excludeKeywords: "",
  isActive: true,
};

function parseKeywordsInput(value: string): string[] {
  const tokens = value
    .split(/[\n,]/g)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);

  const seen = new Set<string>();
  const deduped: string[] = [];
  for (const token of tokens) {
    const key = token.toLowerCase();
    if (!seen.has(key)) {
      deduped.push(token);
      seen.add(key);
    }
  }
  return deduped;
}

function keywordsToInput(value: string[]): string {
  return value.join(", ");
}

function toFormState(stream: DiscoveryStream): DiscoveryFormState {
  return {
    name: stream.name,
    matchQuery: stream.match_query ?? "",
    includeKeywords: keywordsToInput(stream.include_keywords),
    excludeKeywords: keywordsToInput(stream.exclude_keywords),
    isActive: stream.is_active,
  };
}

function recommendationSubtitle(item: FeedRecommendation): string {
  const bits: string[] = [];
  if (item.provider) {
    bits.push(item.provider);
  }
  if (item.site_url) {
    bits.push(item.site_url);
  }
  return bits.join(" • ");
}

export function DiscoveryWorkbench({ mode }: DiscoveryWorkbenchProps) {
  const streamsQuery = useDiscoveryStreamsQuery();
  const summaryQuery = useFeedRecommendationSummaryQuery();
  const createStreamMutation = useCreateDiscoveryStreamMutation();
  const updateStreamMutation = useUpdateDiscoveryStreamMutation();
  const deleteStreamMutation = useDeleteDiscoveryStreamMutation();
  const generateMutation = useGenerateDiscoveryStreamMutation();
  const decideMutation = useDecideFeedRecommendationMutation();
  const resetRecommendationMutation = useResetFeedRecommendationMutation();

  const [selectedStreamId, setSelectedStreamId] = useState<string>("");
  const [form, setForm] = useState<DiscoveryFormState>(DEFAULT_FORM_STATE);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [statusFilter, setStatusFilter] = useState<RecommendationStatusFilter>("pending");
  const [q, setQ] = useState("");

  const streams = useMemo(() => streamsQuery.data ?? [], [streamsQuery.data]);
  const selectedStream = useMemo(
    () => streams.find((item) => item.id === selectedStreamId) ?? null,
    [selectedStreamId, streams]
  );
  const recommendationFilters = useMemo<RecommendationFilters>(() => {
    if (statusFilter === "all") {
      return {
        q,
        sort_by: "updated_at",
        sort_direction: "desc",
        limit: 100,
        offset: 0,
      };
    }
    return {
      status: statusFilter,
      q,
      sort_by: "updated_at",
      sort_direction: "desc",
      limit: 100,
      offset: 0,
    };
  }, [q, statusFilter]);
  const recommendationsQuery = useFeedRecommendationsQuery(recommendationFilters);
  const recommendations = recommendationsQuery.data?.items ?? [];
  const summary = summaryQuery.data;
  const isSaving = createStreamMutation.isPending || updateStreamMutation.isPending;

  const resetForm = () => {
    setSelectedStreamId("");
    setForm(DEFAULT_FORM_STATE);
  };

  const startEdit = (stream: DiscoveryStream) => {
    setSelectedStreamId(stream.id);
    setForm(toFormState(stream));
    setFeedback(null);
  };

  const saveForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const name = form.name.trim();
    const matchQuery = form.matchQuery.trim();
    const includeKeywords = parseKeywordsInput(form.includeKeywords);
    const excludeKeywords = parseKeywordsInput(form.excludeKeywords);

    if (name.length === 0) {
      setFeedback({ severity: "error", message: "Name is required." });
      return;
    }
    if (matchQuery.length === 0 && includeKeywords.length === 0) {
      setFeedback({ severity: "error", message: "Provide a query or include keywords." });
      return;
    }

    try {
      if (selectedStream) {
        await updateStreamMutation.mutateAsync({
          streamId: selectedStream.id,
          payload: {
            name,
            match_query: matchQuery.length > 0 ? matchQuery : null,
            include_keywords: includeKeywords,
            exclude_keywords: excludeKeywords,
            is_active: form.isActive,
          },
        });
        setFeedback({ severity: "success", message: "Discovery stream updated." });
      } else {
        const created = await createStreamMutation.mutateAsync({
          name,
          match_query: matchQuery.length > 0 ? matchQuery : null,
          include_keywords: includeKeywords,
          exclude_keywords: excludeKeywords,
          is_active: form.isActive,
        });
        startEdit(created);
        setFeedback({ severity: "success", message: "Discovery stream created." });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save discovery stream.";
      setFeedback({ severity: "error", message });
    }
  };

  const deleteSelectedStream = async () => {
    if (!selectedStream) {
      return;
    }
    try {
      await deleteStreamMutation.mutateAsync(selectedStream.id);
      resetForm();
      setFeedback({ severity: "success", message: "Discovery stream deleted." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete discovery stream.";
      setFeedback({ severity: "error", message });
    }
  };

  const runGenerate = async () => {
    if (!selectedStream) {
      setFeedback({ severity: "info", message: "Select a discovery stream first." });
      return;
    }
    try {
      const result = await generateMutation.mutateAsync({ streamId: selectedStream.id });
      setFeedback({
        severity: "success",
        message: `Generated ${result.candidate_count} candidates (${result.pending_count} pending, ${result.resolved_existing_count} resolved existing).`,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Discovery generation failed.";
      setFeedback({ severity: "error", message });
    }
  };

  const acceptRecommendation = async (recommendationId: string) => {
    try {
      await decideMutation.mutateAsync({ recommendationId, payload: { decision: "accept" } });
      setFeedback({ severity: "success", message: "Recommendation accepted." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to accept recommendation.";
      setFeedback({ severity: "error", message });
    }
  };

  const denyRecommendation = async (recommendationId: string) => {
    try {
      await decideMutation.mutateAsync({ recommendationId, payload: { decision: "deny" } });
      setFeedback({ severity: "success", message: "Recommendation denied." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to deny recommendation.";
      setFeedback({ severity: "error", message });
    }
  };

  const resetRecommendation = async (recommendationId: string) => {
    try {
      await resetRecommendationMutation.mutateAsync(recommendationId);
      setFeedback({ severity: "success", message: "Recommendation reset to pending." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to reset recommendation.";
      setFeedback({ severity: "error", message });
    }
  };

  return (
    <Stack spacing={1.4}>
      {feedback ? <Alert severity={feedback.severity}>{feedback.message}</Alert> : null}
      <Stack direction={{ xs: "column", lg: "row" }} spacing={1.4}>
        <Paper variant="outlined" sx={{ flex: mode === "settings" ? "0 0 420px" : "0 0 360px", p: 1.4 }}>
          <Stack component="form" spacing={1.1} onSubmit={(event) => void saveForm(event)}>
            <Typography variant="h6">{selectedStream ? "Edit discovery stream" : "Create discovery stream"}</Typography>
            <TextField
              label="Name"
              size="small"
              value={form.name}
              onChange={(event) => setForm((previous) => ({ ...previous, name: event.target.value }))}
              required
            />
            <TextField
              label="Core query"
              size="small"
              value={form.matchQuery}
              onChange={(event) => setForm((previous) => ({ ...previous, matchQuery: event.target.value }))}
              helperText="Optional if include keywords are provided."
            />
            <TextField
              label="Include keywords"
              size="small"
              value={form.includeKeywords}
              onChange={(event) => setForm((previous) => ({ ...previous, includeKeywords: event.target.value }))}
            />
            <TextField
              label="Exclude keywords"
              size="small"
              value={form.excludeKeywords}
              onChange={(event) => setForm((previous) => ({ ...previous, excludeKeywords: event.target.value }))}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={form.isActive}
                  onChange={(event) => setForm((previous) => ({ ...previous, isActive: event.target.checked }))}
                />
              }
              label="Active"
            />
            <Stack direction="row" spacing={1}>
              <Button type="submit" variant="contained" size="small" disabled={isSaving}>
                {selectedStream ? "Save changes" : "Create stream"}
              </Button>
              <Button type="button" variant="text" size="small" onClick={resetForm}>
                New
              </Button>
              {selectedStream ? (
                <Tooltip title="Delete stream">
                  <IconButton
                    aria-label={`Delete discovery stream ${selectedStream.name}`}
                    size="small"
                    onClick={() => void deleteSelectedStream()}
                  >
                    <DeleteOutlineRoundedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              ) : null}
            </Stack>
            {streamsQuery.isError ? <Alert severity="error">Failed to load discovery streams.</Alert> : null}
            {streams.length > 0 ? (
              <Stack spacing={0.5} sx={{ pt: 0.6 }}>
                <Typography variant="caption" color="text.secondary">
                  Existing streams
                </Typography>
                {streams.map((stream) => (
                  <Button
                    key={stream.id}
                    variant={selectedStreamId === stream.id ? "contained" : "text"}
                    size="small"
                    sx={{ justifyContent: "flex-start" }}
                    onClick={() => startEdit(stream)}
                  >
                    {stream.name}
                  </Button>
                ))}
              </Stack>
            ) : null}
          </Stack>
        </Paper>

        <Paper variant="outlined" sx={{ flex: "1 1 auto", p: 1.4 }}>
          <Stack spacing={1.1}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id="discovery-stream-select-label">Stream</InputLabel>
                <Select
                  labelId="discovery-stream-select-label"
                  label="Stream"
                  value={selectedStreamId}
                  onChange={(event) => {
                    const stream = streams.find((item) => item.id === event.target.value);
                    if (stream) {
                      startEdit(stream);
                    }
                  }}
                >
                  {streams.map((stream) => (
                    <MenuItem key={stream.id} value={stream.id}>
                      {stream.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                variant="outlined"
                size="small"
                startIcon={<PlayArrowRoundedIcon fontSize="small" />}
                onClick={() => void runGenerate()}
                disabled={generateMutation.isPending || streams.length === 0}
              >
                Generate
              </Button>
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel id="discovery-status-filter-label">Status</InputLabel>
                <Select<RecommendationStatusFilter>
                  labelId="discovery-status-filter-label"
                  label="Status"
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="pending">Pending</MenuItem>
                  <MenuItem value="accepted">Accepted</MenuItem>
                  <MenuItem value="denied">Denied</MenuItem>
                  <MenuItem value="resolved_existing">Resolved existing</MenuItem>
                </Select>
              </FormControl>
              <TextField
                size="small"
                value={q}
                onChange={(event) => setQ(event.target.value)}
                placeholder="Search recommendations"
                InputProps={{
                  startAdornment: <SearchRoundedIcon fontSize="small" sx={{ mr: 0.5, opacity: 0.6 }} />,
                }}
              />
            </Stack>

            <Stack direction="row" spacing={0.8} flexWrap="wrap">
              <Chip size="small" label={`Pending: ${summary?.pending_count ?? 0}`} />
              <Chip size="small" label={`Accepted: ${summary?.accepted_count ?? 0}`} />
              <Chip size="small" label={`Denied: ${summary?.denied_count ?? 0}`} />
              <Chip size="small" label={`Resolved: ${summary?.resolved_existing_count ?? 0}`} />
            </Stack>

            {recommendationsQuery.isError ? (
              <Alert severity="error">Failed to load feed recommendations.</Alert>
            ) : null}
            {recommendations.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No recommendations yet. Run generation for a discovery stream.
              </Typography>
            ) : (
              <Stack spacing={0.8}>
                {recommendations.map((recommendation) => (
                  <Paper key={recommendation.id} variant="outlined" sx={{ p: 1 }}>
                    <Stack spacing={0.7}>
                      <Stack direction="row" justifyContent="space-between" spacing={1}>
                        <Box sx={{ minWidth: 0 }}>
                          <Typography variant="subtitle2" noWrap>
                            {recommendation.feed_title || recommendation.feed_url}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" noWrap>
                            {recommendation.feed_url}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                            {recommendationSubtitle(recommendation)}
                          </Typography>
                        </Box>
                        <Chip size="small" label={recommendation.status.replace("_", " ")} />
                      </Stack>
                      <Stack direction="row" spacing={0.8}>
                        {recommendation.status === "pending" ? (
                          <>
                            <Button
                              size="small"
                              variant="contained"
                              onClick={() => void acceptRecommendation(recommendation.id)}
                              disabled={decideMutation.isPending}
                            >
                              Accept
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => void denyRecommendation(recommendation.id)}
                              disabled={decideMutation.isPending}
                            >
                              Deny
                            </Button>
                          </>
                        ) : null}
                        {recommendation.status === "denied" ? (
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => void resetRecommendation(recommendation.id)}
                            disabled={resetRecommendationMutation.isPending}
                          >
                            Reset
                          </Button>
                        ) : null}
                      </Stack>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            )}
          </Stack>
        </Paper>
      </Stack>
    </Stack>
  );
}
