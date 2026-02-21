import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import {
  Alert,
  Box,
  Button,
  Collapse,
  CircularProgress,
  Divider,
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

import { useFoldersQuery } from "../../workspace/api/workspaceHooks";
import { SettingsLayout } from "../../settings/components/SettingsLayout";
import { ApiError } from "../../../shared/api/client";
import type {
  KeywordStream,
  KeywordStreamCreateRequest,
  KeywordStreamUpdateRequest,
} from "../../../shared/types/contracts";
import {
  useCreateStreamMutation,
  useDeleteStreamMutation,
  useRunStreamBackfillMutation,
  useStreamsQuery,
  useUpdateStreamMutation,
} from "../api/monitoringHooks";

type ClassifierMode = "rules_only" | "classifier_only" | "hybrid";

type StreamFormState = {
  name: string;
  description: string;
  folderId: string;
  isActive: boolean;
  priority: string;
  matchQuery: string;
  includeKeywords: string;
  excludeKeywords: string;
  includeRegex: string;
  excludeRegex: string;
  sourceContains: string;
  languageEquals: string;
  classifierMode: ClassifierMode;
  classifierPlugin: string;
  classifierConfig: string;
  classifierMinConfidence: string;
};

const DEFAULT_FORM_STATE: StreamFormState = {
  name: "",
  description: "",
  folderId: "",
  isActive: true,
  priority: "100",
  matchQuery: "",
  includeKeywords: "",
  excludeKeywords: "",
  includeRegex: "",
  excludeRegex: "",
  sourceContains: "",
  languageEquals: "",
  classifierMode: "rules_only",
  classifierPlugin: "",
  classifierConfig: "",
  classifierMinConfidence: "0.7",
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

function parseRegexInput(value: string): string[] {
  const tokens = value
    .split(/\n/g)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);

  const seen = new Set<string>();
  const deduped: string[] = [];
  for (const token of tokens) {
    if (!seen.has(token)) {
      deduped.push(token);
      seen.add(token);
    }
  }
  return deduped;
}

function regexToInput(value: string[]): string {
  return value.join("\n");
}

function toFormState(stream: KeywordStream): StreamFormState {
  const classifierConfig =
    stream.classifier_config && Object.keys(stream.classifier_config).length > 0
      ? JSON.stringify(stream.classifier_config, null, 2)
      : "";
  return {
    name: stream.name,
    description: stream.description ?? "",
    folderId: stream.folder_id ?? "",
    isActive: stream.is_active,
    priority: String(stream.priority),
    matchQuery: stream.match_query ?? "",
    includeKeywords: keywordsToInput(stream.include_keywords),
    excludeKeywords: keywordsToInput(stream.exclude_keywords),
    includeRegex: regexToInput(stream.include_regex),
    excludeRegex: regexToInput(stream.exclude_regex),
    sourceContains: stream.source_contains ?? "",
    languageEquals: stream.language_equals ?? "",
    classifierMode: stream.classifier_mode,
    classifierPlugin: stream.classifier_plugin ?? "",
    classifierConfig,
    classifierMinConfidence: String(stream.classifier_min_confidence),
  };
}

function toNumber(value: string, fallback: number): number {
  const normalized = Number(value);
  return Number.isFinite(normalized) ? normalized : fallback;
}

function formatMode(mode: ClassifierMode): string {
  if (mode === "rules_only") {
    return "Rules only";
  }
  if (mode === "classifier_only") {
    return "Classifier only";
  }
  return "Hybrid";
}

function hasAdvancedConfig(stream: KeywordStream): boolean {
  return (
    stream.priority !== 100 ||
    stream.include_regex.length > 0 ||
    stream.exclude_regex.length > 0 ||
    (stream.source_contains ?? "").length > 0 ||
    (stream.language_equals ?? "").length > 0 ||
    stream.classifier_mode !== "rules_only" ||
    (stream.classifier_plugin ?? "").length > 0 ||
    Object.keys(stream.classifier_config ?? {}).length > 0 ||
    stream.classifier_min_confidence !== 0.7
  );
}

type Feedback = {
  severity: "success" | "error" | "info";
  message: string;
};

export function MonitoringFeedsPage() {
  const streamsQuery = useStreamsQuery();
  const foldersQuery = useFoldersQuery();
  const createStreamMutation = useCreateStreamMutation();
  const updateStreamMutation = useUpdateStreamMutation();
  const deleteStreamMutation = useDeleteStreamMutation();
  const runBackfillMutation = useRunStreamBackfillMutation();

  const [editingStreamId, setEditingStreamId] = useState<string | null>(null);
  const [form, setForm] = useState<StreamFormState>(DEFAULT_FORM_STATE);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const streams = streamsQuery.data;
  const streamItems = streams ?? [];
  const folderOptions = useMemo(() => foldersQuery.data ?? [], [foldersQuery.data]);
  const folderNameById = useMemo(
    () => new Map(folderOptions.map((folder) => [folder.id, folder.name] as const)),
    [folderOptions]
  );
  const editingStream = useMemo(
    () => (streams ?? []).find((stream) => stream.id === editingStreamId) ?? null,
    [editingStreamId, streams]
  );
  const isEditing = editingStream !== null;
  const isSaving = createStreamMutation.isPending || updateStreamMutation.isPending;

  const resetForm = () => {
    setEditingStreamId(null);
    setForm(DEFAULT_FORM_STATE);
    setShowAdvanced(false);
    setSubmitError(null);
  };

  const startEdit = (stream: KeywordStream) => {
    setEditingStreamId(stream.id);
    setForm(toFormState(stream));
    setShowAdvanced(hasAdvancedConfig(stream));
    setSubmitError(null);
    setFeedback(null);
  };

  const submitForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    setFeedback(null);

    const name = form.name.trim();
    const description = form.description.trim();
    const matchQuery = form.matchQuery.trim();
    const sourceContains = form.sourceContains.trim();
    const languageEquals = form.languageEquals.trim();
    const classifierPlugin = form.classifierPlugin.trim();
    const classifierConfigRaw = form.classifierConfig.trim();
    const includeKeywords = parseKeywordsInput(form.includeKeywords);
    const excludeKeywords = parseKeywordsInput(form.excludeKeywords);
    const includeRegex = parseRegexInput(form.includeRegex);
    const excludeRegex = parseRegexInput(form.excludeRegex);
    let classifierConfig: Record<string, unknown> | null = null;

    if (name.length === 0) {
      setSubmitError("Name is required.");
      return;
    }

    const classifierEnabled = form.classifierMode !== "rules_only";
    const hasPositiveCriteria =
      matchQuery.length > 0 ||
      includeKeywords.length > 0 ||
      includeRegex.length > 0 ||
      sourceContains.length > 0 ||
      languageEquals.length > 0;
    if (!hasPositiveCriteria && !classifierEnabled) {
      setSubmitError("Provide at least one positive rule (query, keyword, regex, source URL, or language).");
      return;
    }
    if (classifierEnabled && classifierPlugin.length === 0) {
      setSubmitError("Classifier plugin is required when classifier mode is enabled.");
      return;
    }
    if (classifierConfigRaw.length > 0) {
      try {
        const parsed = JSON.parse(classifierConfigRaw) as unknown;
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          setSubmitError("Classifier config must be a JSON object.");
          return;
        }
        classifierConfig = parsed as Record<string, unknown>;
      } catch {
        setSubmitError("Classifier config must be valid JSON.");
        return;
      }
    }

    const priority = Math.max(0, Math.min(10_000, toNumber(form.priority, 100)));
    const classifierMinConfidence = Math.max(
      0,
      Math.min(1, toNumber(form.classifierMinConfidence, 0.7))
    );

    try {
      if (isEditing && editingStreamId) {
        const payload: KeywordStreamUpdateRequest = {
          name,
          description: description.length > 0 ? description : null,
          folder_id: form.folderId.length > 0 ? form.folderId : null,
          is_active: form.isActive,
          priority,
          match_query: matchQuery.length > 0 ? matchQuery : null,
          include_keywords: includeKeywords,
          exclude_keywords: excludeKeywords,
          include_regex: includeRegex,
          exclude_regex: excludeRegex,
          source_contains: sourceContains.length > 0 ? sourceContains : null,
          language_equals: languageEquals.length > 0 ? languageEquals : null,
          classifier_mode: form.classifierMode,
          classifier_plugin: classifierEnabled ? classifierPlugin : null,
          classifier_config: classifierConfig,
          classifier_min_confidence: classifierMinConfidence,
        };
        await updateStreamMutation.mutateAsync({ streamId: editingStreamId, payload });
        setFeedback({ severity: "success", message: "Monitoring feed updated." });
      } else {
        const payload: KeywordStreamCreateRequest = {
          name,
          description: description.length > 0 ? description : null,
          folder_id: form.folderId.length > 0 ? form.folderId : null,
          is_active: form.isActive,
          priority,
          match_query: matchQuery.length > 0 ? matchQuery : null,
          include_keywords: includeKeywords,
          exclude_keywords: excludeKeywords,
          include_regex: includeRegex,
          exclude_regex: excludeRegex,
          source_contains: sourceContains.length > 0 ? sourceContains : null,
          language_equals: languageEquals.length > 0 ? languageEquals : null,
          classifier_mode: form.classifierMode,
          classifier_plugin: classifierEnabled ? classifierPlugin : null,
          classifier_config: classifierConfig,
          classifier_min_confidence: classifierMinConfidence,
        };
        await createStreamMutation.mutateAsync(payload);
        setFeedback({ severity: "success", message: "Monitoring feed created." });
      }
      resetForm();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save monitoring feed.";
      setSubmitError(message);
    }
  };

  const deleteStreamById = async (streamId: string) => {
    setFeedback(null);
    setSubmitError(null);
    try {
      await deleteStreamMutation.mutateAsync(streamId);
      if (editingStreamId === streamId) {
        resetForm();
      }
      setFeedback({ severity: "success", message: "Monitoring feed deleted." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete monitoring feed.";
      setFeedback({ severity: "error", message });
    }
  };

  const toggleActive = async (stream: KeywordStream) => {
    setFeedback(null);
    try {
      await updateStreamMutation.mutateAsync({
        streamId: stream.id,
        payload: { is_active: !stream.is_active },
      });
      setFeedback({
        severity: "success",
        message: `Monitoring feed ${stream.is_active ? "disabled" : "enabled"}.`,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update monitoring feed state.";
      setFeedback({ severity: "error", message });
    }
  };

  const runBackfill = async (streamId: string) => {
    setFeedback(null);
    try {
      const result = await runBackfillMutation.mutateAsync(streamId);
      setFeedback({
        severity: "success",
        message: `Backfill completed: ${result.matched_count} matched of ${result.scanned_count} scanned.`,
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setFeedback({
          severity: "info",
          message: "Backfill endpoint is not available yet in this build.",
        });
        return;
      }
      const message = error instanceof Error ? error.message : "Failed to run backfill.";
      setFeedback({ severity: "error", message });
    }
  };

  return (
    <SettingsLayout
      activeSection="monitoring"
      title="Monitoring feeds"
      headingId="monitoring-heading"
      maxWidth={1260}
      description="Manage monitoring definitions, matching configuration, and backfill execution."
    >

      {feedback ? <Alert severity={feedback.severity}>{feedback.message}</Alert> : null}
      {streamsQuery.isError ? (
        <Alert severity="error">Failed to load monitoring feeds.</Alert>
      ) : null}

      <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
          <Paper variant="outlined" sx={{ flex: "0 0 420px", p: 2 }}>
            <Typography variant="h6" component="h2">
              {isEditing ? "Edit monitoring feed" : "Create monitoring feed"}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.6 }}>
              Define match rules first, then add optional classifier behavior.
            </Typography>
            <Box component="form" onSubmit={(event) => void submitForm(event)} sx={{ mt: 1.6 }}>
              <Stack spacing={1.2}>
                <Typography variant="subtitle2" color="text.secondary">
                  Basics
                </Typography>
                <TextField
                  label="Name"
                  size="small"
                  value={form.name}
                  onChange={(event) => setForm((previous) => ({ ...previous, name: event.target.value }))}
                  required
                />
                <TextField
                  label="Description"
                  size="small"
                  value={form.description}
                  onChange={(event) =>
                    setForm((previous) => ({ ...previous, description: event.target.value }))
                  }
                />
                <FormControl size="small">
                  <InputLabel id="monitoring-folder-label">Folder</InputLabel>
                  <Select
                    labelId="monitoring-folder-label"
                    label="Folder"
                    value={form.folderId}
                    onChange={(event) =>
                      setForm((previous) => ({ ...previous, folderId: event.target.value }))
                    }
                  >
                    <MenuItem value="">Unfiled</MenuItem>
                    {folderOptions.map((folder) => (
                      <MenuItem key={folder.id} value={folder.id}>
                        {folder.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControlLabel
                  control={
                    <Switch
                      checked={form.isActive}
                      onChange={(event) =>
                        setForm((previous) => ({ ...previous, isActive: event.target.checked }))
                      }
                    />
                  }
                  label="Active"
                />
                <Divider sx={{ my: 0.4 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  Match Rules
                </Typography>
                <TextField
                  label="Core search query (v1)"
                  size="small"
                  value={form.matchQuery}
                  onChange={(event) =>
                    setForm((previous) => ({ ...previous, matchQuery: event.target.value }))
                  }
                  helperText='Supports AND/OR/NOT, quotes, (), suffix wildcard (*), and fuzzy term~1/term~2.'
                />
                <TextField
                  label="Include keywords"
                  size="small"
                  value={form.includeKeywords}
                  onChange={(event) =>
                    setForm((previous) => ({ ...previous, includeKeywords: event.target.value }))
                  }
                  helperText="Comma or newline separated"
                />
                <TextField
                  label="Exclude keywords"
                  size="small"
                  value={form.excludeKeywords}
                  onChange={(event) =>
                    setForm((previous) => ({ ...previous, excludeKeywords: event.target.value }))
                  }
                  helperText="Comma or newline separated"
                />
                <Button
                  type="button"
                  size="small"
                  variant="text"
                  onClick={() => setShowAdvanced((previous) => !previous)}
                  sx={{ alignSelf: "flex-start" }}
                >
                  {showAdvanced ? "Hide advanced options" : "Show advanced options"}
                </Button>
                <Collapse in={showAdvanced} unmountOnExit>
                  <Stack spacing={1.2}>
                    <Divider sx={{ my: 0.4 }} />
                    <Typography variant="subtitle2" color="text.secondary">
                      Advanced Match Rules
                    </Typography>
                    <TextField
                      label="Priority"
                      size="small"
                      type="number"
                      inputProps={{ min: 0, max: 10000 }}
                      value={form.priority}
                      onChange={(event) => setForm((previous) => ({ ...previous, priority: event.target.value }))}
                      helperText="Lower values are evaluated earlier."
                    />
                    <TextField
                      label="Include regex"
                      size="small"
                      multiline
                      minRows={2}
                      value={form.includeRegex}
                      onChange={(event) =>
                        setForm((previous) => ({ ...previous, includeRegex: event.target.value }))
                      }
                      helperText="One regex pattern per line"
                    />
                    <TextField
                      label="Exclude regex"
                      size="small"
                      multiline
                      minRows={2}
                      value={form.excludeRegex}
                      onChange={(event) =>
                        setForm((previous) => ({ ...previous, excludeRegex: event.target.value }))
                      }
                      helperText="One regex pattern per line"
                    />
                    <TextField
                      label="Source URL contains"
                      size="small"
                      value={form.sourceContains}
                      onChange={(event) =>
                        setForm((previous) => ({ ...previous, sourceContains: event.target.value }))
                      }
                      placeholder="example.com"
                      helperText="Case-insensitive match against source URL/domain."
                    />
                    <TextField
                      label="Language code equals"
                      size="small"
                      value={form.languageEquals}
                      onChange={(event) =>
                        setForm((previous) => ({ ...previous, languageEquals: event.target.value }))
                      }
                      placeholder="en"
                      helperText="Use feed language code (for example: en, fr, de)."
                    />
                    <Divider sx={{ my: 0.4 }} />
                    <Typography variant="subtitle2" color="text.secondary">
                      Classifier (Optional)
                    </Typography>
                    <FormControl size="small">
                      <InputLabel id="monitoring-classifier-mode-label">Classifier mode</InputLabel>
                      <Select
                        labelId="monitoring-classifier-mode-label"
                        label="Classifier mode"
                        value={form.classifierMode}
                        onChange={(event) =>
                          setForm((previous) => ({
                            ...previous,
                            classifierMode: event.target.value as ClassifierMode,
                          }))
                        }
                      >
                        <MenuItem value="rules_only">Rules only</MenuItem>
                        <MenuItem value="classifier_only">Classifier only</MenuItem>
                        <MenuItem value="hybrid">Hybrid</MenuItem>
                      </Select>
                    </FormControl>
                    <TextField
                      label="Classifier plugin"
                      size="small"
                      value={form.classifierPlugin}
                      onChange={(event) =>
                        setForm((previous) => ({ ...previous, classifierPlugin: event.target.value }))
                      }
                      disabled={form.classifierMode === "rules_only"}
                      helperText={
                        form.classifierMode === "rules_only"
                          ? "Not required for rules-only mode."
                          : "Required for classifier-enabled modes."
                      }
                    />
                    <TextField
                      label="Classifier config (JSON)"
                      size="small"
                      multiline
                      minRows={3}
                      value={form.classifierConfig}
                      onChange={(event) =>
                        setForm((previous) => ({ ...previous, classifierConfig: event.target.value }))
                      }
                      disabled={form.classifierMode === "rules_only"}
                      helperText={
                        form.classifierMode === "rules_only"
                          ? "Optional when rules-only mode is selected."
                          : "Optional JSON object passed to classifier plugin."
                      }
                    />
                    <TextField
                      label="Classifier min confidence"
                      size="small"
                      type="number"
                      inputProps={{ min: 0, max: 1, step: 0.05 }}
                      value={form.classifierMinConfidence}
                      onChange={(event) =>
                        setForm((previous) => ({
                          ...previous,
                          classifierMinConfidence: event.target.value,
                        }))
                      }
                      helperText="Used in classifier-only or hybrid modes."
                    />
                  </Stack>
                </Collapse>
                {submitError ? <Alert severity="error">{submitError}</Alert> : null}
                <Stack direction="row" spacing={1} justifyContent="flex-end">
                  {isEditing ? (
                    <Button type="button" size="small" variant="text" onClick={resetForm}>
                      Cancel
                    </Button>
                  ) : null}
                  <Button type="submit" size="small" variant="contained" disabled={isSaving}>
                    {isEditing ? "Save changes" : "Create monitoring feed"}
                  </Button>
                </Stack>
              </Stack>
            </Box>
          </Paper>

        <Typography variant="caption" className="table-scroll-hint">
          Tip: scroll horizontally to see query, active, and action columns.
        </Typography>

        <Paper variant="outlined" sx={{ flex: "1 1 auto", p: 1.2 }} className="monitoring-table">
          <Stack spacing={0.4} className="monitoring-table__rows">
            <Stack
              direction="row"
              sx={{ px: 1, py: 0.7, borderBottom: "1px solid", borderColor: "divider" }}
              alignItems="center"
              spacing={1}
            >
              <Typography variant="caption" sx={{ flex: 2.2, fontWeight: 700 }}>
                Name
              </Typography>
              <Typography variant="caption" sx={{ flex: 1, fontWeight: 700 }}>
                Folder
              </Typography>
              <Typography variant="caption" sx={{ flex: 1, fontWeight: 700 }}>
                Mode
              </Typography>
              <Typography variant="caption" sx={{ width: 72, fontWeight: 700 }}>
                Priority
              </Typography>
              <Typography variant="caption" sx={{ width: 72, fontWeight: 700 }}>
                Query
              </Typography>
              <Typography variant="caption" sx={{ width: 66, fontWeight: 700 }}>
                Active
              </Typography>
              <Typography variant="caption" sx={{ width: 114, fontWeight: 700, textAlign: "right" }}>
                Actions
              </Typography>
            </Stack>

            {streamsQuery.isLoading ? (
              <Box sx={{ py: 2, px: 1 }}>
                <CircularProgress size={22} />
              </Box>
            ) : null}
            {!streamsQuery.isLoading && streamItems.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ px: 1, py: 1.2 }}>
                No monitoring feeds yet.
              </Typography>
            ) : null}

            {streamItems.map((stream) => {
              const isEditingRow = editingStreamId === stream.id;
              return (
                <Stack
                  key={stream.id}
                  direction="row"
                  alignItems="center"
                  spacing={1}
                  role="button"
                  tabIndex={0}
                  aria-label={`Select monitoring feed ${stream.name}`}
                  onClick={() => startEdit(stream)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      startEdit(stream);
                    }
                  }}
                  sx={{
                    px: 1,
                    py: 0.55,
                    borderRadius: 1,
                    backgroundColor: isEditingRow ? "action.selected" : "transparent",
                    cursor: "pointer",
                  }}
                  className="monitoring-table__row"
                >
                  <Box sx={{ flex: 2.2, minWidth: 0 }} className="monitoring-table__name-cell">
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 600,
                        whiteSpace: "normal",
                        wordBreak: "break-word",
                        lineHeight: 1.25,
                      }}
                    >
                      {stream.name}
                    </Typography>
                  </Box>
                  <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                    {stream.folder_id ? (folderNameById.get(stream.folder_id) ?? "Folder") : "Unfiled"}
                  </Typography>
                  <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                    {formatMode(stream.classifier_mode)}
                  </Typography>
                  <Typography variant="body2" sx={{ width: 72 }}>
                    {stream.priority}
                  </Typography>
                  <Typography variant="body2" sx={{ width: 72 }}>
                    {stream.match_query ? "Yes" : "No"}
                  </Typography>
                  <Box sx={{ width: 66 }}>
                    <Switch
                      size="small"
                      checked={stream.is_active}
                      inputProps={{ "aria-label": `Toggle active for ${stream.name}` }}
                      onClick={(event) => {
                        event.stopPropagation();
                      }}
                      onChange={() => void toggleActive(stream)}
                    />
                  </Box>
                  <Stack direction="row" spacing={0.2} sx={{ width: 114, justifyContent: "flex-end" }}>
                    <Tooltip title="Run backfill">
                      <IconButton
                        size="small"
                        aria-label={`Run backfill for ${stream.name}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          void runBackfill(stream.id);
                        }}
                        disabled={runBackfillMutation.isPending}
                      >
                        <PlayArrowRoundedIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        color="error"
                        aria-label={`Delete ${stream.name}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          void deleteStreamById(stream.id);
                        }}
                        disabled={deleteStreamMutation.isPending}
                      >
                        <DeleteOutlineRoundedIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </Stack>
              );
            })}
          </Stack>
        </Paper>
        </Stack>
    </SettingsLayout>
  );
}
