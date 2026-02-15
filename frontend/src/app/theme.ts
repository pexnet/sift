import { createTheme } from "@mui/material/styles";

export type ThemeMode = "light" | "dark";

export function createAppTheme(mode: ThemeMode) {
  return createTheme({
    palette: {
      mode,
    },
    shape: {
      borderRadius: 10,
    },
  });
}
