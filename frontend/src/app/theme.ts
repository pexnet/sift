import { alpha, createTheme } from "@mui/material/styles";

import type { ThemeMode, ThemePreset } from "./uiPreferences";

type PresetTone = {
  primary: string;
  background: string;
  surface: string;
  text: string;
  muted: string;
  border: string;
};

const PRESET_TONES: Record<ThemePreset, Record<ThemeMode, PresetTone>> = {
  classic: {
    light: {
      primary: "#3fbf73",
      background: "#eff5ec",
      surface: "#f7f9f3",
      text: "#1f2f27",
      muted: "#5f7264",
      border: "#ccd9c9",
    },
    dark: {
      primary: "#63d191",
      background: "#0f1622",
      surface: "#151f2d",
      text: "#eaf1ff",
      muted: "#9bb0cf",
      border: "#2c3950",
    },
  },
  ocean: {
    light: {
      primary: "#2693d8",
      background: "#ecf5fb",
      surface: "#f4f9fd",
      text: "#1d2f42",
      muted: "#5d7387",
      border: "#c7d9e8",
    },
    dark: {
      primary: "#63bae7",
      background: "#0d1923",
      surface: "#132332",
      text: "#e4f1ff",
      muted: "#9db8d0",
      border: "#2b445c",
    },
  },
  graphite: {
    light: {
      primary: "#7c63f2",
      background: "#f1eef8",
      surface: "#f8f5fc",
      text: "#2b2442",
      muted: "#676082",
      border: "#d4cbe7",
    },
    dark: {
      primary: "#a08fff",
      background: "#151324",
      surface: "#1b1930",
      text: "#efeafd",
      muted: "#b3aad9",
      border: "#3b3558",
    },
  },
  sand: {
    light: {
      primary: "#c9782e",
      background: "#f8f1e8",
      surface: "#fcf6ee",
      text: "#3f2f22",
      muted: "#786251",
      border: "#e0cfbb",
    },
    dark: {
      primary: "#dea774",
      background: "#1d1712",
      surface: "#241d17",
      text: "#f5eee5",
      muted: "#c6b6a5",
      border: "#4a3b2e",
    },
  },
};

export function createAppTheme(mode: ThemeMode, preset: ThemePreset) {
  const tone = PRESET_TONES[preset][mode];

  return createTheme({
    palette: {
      mode,
      primary: {
        main: tone.primary,
      },
      background: {
        default: tone.background,
        paper: tone.surface,
      },
      text: {
        primary: tone.text,
        secondary: tone.muted,
      },
      divider: tone.border,
      action: {
        hover: alpha(tone.primary, mode === "dark" ? 0.18 : 0.08),
        selected: alpha(tone.primary, mode === "dark" ? 0.26 : 0.14),
      },
    },
    shape: {
      borderRadius: 10,
    },
  });
}
