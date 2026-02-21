import {
  Button,
  CircularProgress,
  Divider,
  FormControl,
  FormHelperText,
  FormLabel,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import type { KeyboardEvent } from "react";

import { useAppUiState } from "../../../app/providers";
import { NAV_PRESET_OPTIONS, THEME_PRESET_OPTIONS, type DensityMode } from "../../../app/uiPreferences";
import { SettingsLayout } from "../../settings/components/SettingsLayout";
import { useCurrentUser } from "../api/authHooks";

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <Stack
      direction="row"
      sx={{
        borderBottom: "1px solid",
        borderColor: "divider",
        py: 1,
      }}
      justifyContent="space-between"
      spacing={2}
    >
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1">{value}</Typography>
    </Stack>
  );
}

function getNextOptionIndex(currentIndex: number, direction: 1 | -1, length: number): number {
  return (currentIndex + direction + length) % length;
}

function handleToggleGroupArrowKeys<T extends string>(
  event: KeyboardEvent<HTMLElement>,
  currentValue: T,
  values: readonly T[],
  setValue: (value: T) => void
): void {
  if (values.length === 0) {
    return;
  }

  let nextIndex: number | null = null;
  const currentIndex = Math.max(0, values.indexOf(currentValue));

  if (event.key === "ArrowRight" || event.key === "ArrowDown") {
    nextIndex = getNextOptionIndex(currentIndex, 1, values.length);
  } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
    nextIndex = getNextOptionIndex(currentIndex, -1, values.length);
  } else if (event.key === "Home") {
    nextIndex = 0;
  } else if (event.key === "End") {
    nextIndex = values.length - 1;
  }

  if (nextIndex === null) {
    return;
  }

  event.preventDefault();
  const nextValue = values[nextIndex];
  if (!nextValue) {
    return;
  }
  setValue(nextValue);
  const nextButton = event.currentTarget.querySelector<HTMLButtonElement>(`button[value="${nextValue}"]`);
  nextButton?.focus();
}

export function AccountPage() {
  const {
    density,
    navPreset,
    resetUiPreferences,
    setDensity,
    setNavPreset,
    setThemeMode,
    setThemePreset,
    themeMode,
    themePreset,
  } = useAppUiState();
  const currentUserQuery = useCurrentUser();

  return (
    <SettingsLayout
      activeSection="general"
      title="Settings"
      headingId="settings-heading"
      maxWidth={1100}
      description="Appearance and layout preferences, plus account identity summary."
      actions={
        <Button className="settings-reset-button" size="small" variant="outlined" onClick={resetUiPreferences}>
          Reset to defaults
        </Button>
      }
    >
      <Typography className="settings-status-note" role="status" aria-live="polite">
        Changes are saved automatically.
      </Typography>

      <Stack spacing={3}>
        <Stack spacing={1.2}>
          <Typography variant="h6" component="h2">
            Appearance
          </Typography>
          <FormControl component="fieldset" className="settings-control-row">
            <FormLabel id="settings-theme-mode-label" component="legend">
              Theme mode
            </FormLabel>
            <ToggleButtonGroup
              className="settings-toggle-group"
              size="small"
              exclusive
              value={themeMode}
              onKeyDown={(event) =>
                handleToggleGroupArrowKeys(
                  event,
                  themeMode,
                  ["light", "dark"] as const,
                  setThemeMode
                )
              }
              onChange={(_, value: "light" | "dark" | null) => {
                if (value) {
                  setThemeMode(value);
                }
              }}
              aria-labelledby="settings-theme-mode-label"
              aria-describedby="settings-theme-mode-help"
            >
              <ToggleButton value="light">Light</ToggleButton>
              <ToggleButton value="dark">Dark</ToggleButton>
            </ToggleButtonGroup>
            <FormHelperText id="settings-theme-mode-help">Use arrow keys to move options and Enter or Space to select.</FormHelperText>
          </FormControl>
          <FormControl component="fieldset" className="settings-control-row">
            <FormLabel id="settings-theme-preset-label" component="legend">
              Theme preset
            </FormLabel>
            <ToggleButtonGroup
              className="settings-toggle-group settings-toggle-group--wrap"
              size="small"
              exclusive
              value={themePreset}
              onKeyDown={(event) =>
                handleToggleGroupArrowKeys(
                  event,
                  themePreset,
                  THEME_PRESET_OPTIONS.map((preset) => preset.value),
                  setThemePreset
                )
              }
              onChange={(_, value: typeof themePreset | null) => {
                if (value) {
                  setThemePreset(value);
                }
              }}
              aria-labelledby="settings-theme-preset-label"
            >
              {THEME_PRESET_OPTIONS.map((preset) => (
                <ToggleButton key={preset.value} value={preset.value}>
                  {preset.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </FormControl>
        </Stack>

        <Divider />

        <Stack spacing={1.2}>
          <Typography variant="h6" component="h2">
            Reading and layout
          </Typography>
          <FormControl component="fieldset" className="settings-control-row">
            <FormLabel id="settings-density-label" component="legend">
              Density
            </FormLabel>
            <ToggleButtonGroup
              className="settings-toggle-group"
              size="small"
              exclusive
              value={density}
              onKeyDown={(event) =>
                handleToggleGroupArrowKeys(
                  event,
                  density,
                  ["compact", "comfortable"] as const,
                  setDensity
                )
              }
              onChange={(_, value: DensityMode | null) => {
                if (value) {
                  setDensity(value);
                }
              }}
              aria-labelledby="settings-density-label"
            >
              <ToggleButton value="compact">Compact</ToggleButton>
              <ToggleButton value="comfortable">Comfortable</ToggleButton>
            </ToggleButtonGroup>
          </FormControl>
          <FormControl component="fieldset" className="settings-control-row">
            <FormLabel id="settings-nav-preset-label" component="legend">
              Navigation preset
            </FormLabel>
            <ToggleButtonGroup
              className="settings-toggle-group"
              size="small"
              exclusive
              value={navPreset}
              onKeyDown={(event) =>
                handleToggleGroupArrowKeys(
                  event,
                  navPreset,
                  NAV_PRESET_OPTIONS.map((preset) => preset.value),
                  setNavPreset
                )
              }
              onChange={(_, value: typeof navPreset | null) => {
                if (value) {
                  setNavPreset(value);
                }
              }}
              aria-labelledby="settings-nav-preset-label"
            >
              {NAV_PRESET_OPTIONS.map((preset) => (
                <ToggleButton key={preset.value} value={preset.value}>
                  {preset.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </FormControl>
        </Stack>

        <Divider />

        <Stack spacing={1.2}>
          <Typography variant="h6" component="h2">
            Account
          </Typography>
          {currentUserQuery.isLoading ? <CircularProgress size={20} /> : null}
          {currentUserQuery.data ? (
            <Stack>
              <InfoRow label="Email" value={currentUserQuery.data.email} />
              <InfoRow label="Display Name" value={currentUserQuery.data.display_name || "(not set)"} />
              <InfoRow label="Admin" value={currentUserQuery.data.is_admin ? "yes" : "no"} />
            </Stack>
          ) : null}
        </Stack>
      </Stack>
    </SettingsLayout>
  );
}
