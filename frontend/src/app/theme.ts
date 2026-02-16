import { createTheme } from "@mui/material/styles";

import type { ThemeMode, ThemePreset } from "./uiPreferences";

const PRESET_PRIMARY: Record<ThemePreset, { light: string; dark: string }> = {
  classic: { light: "#3fbf73", dark: "#63d191" },
  ocean: { light: "#2693d8", dark: "#63bae7" },
  graphite: { light: "#7c63f2", dark: "#a08fff" },
  sand: { light: "#c9782e", dark: "#dea774" },
};

export function createAppTheme(mode: ThemeMode, preset: ThemePreset) {
  return createTheme({
    palette: {
      mode,
      primary: {
        main: PRESET_PRIMARY[preset][mode],
      },
    },
    shape: {
      borderRadius: 10,
    },
  });
}
