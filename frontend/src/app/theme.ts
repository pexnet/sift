import { createTheme } from "@mui/material/styles";

export type ThemeMode = "light" | "dark";

export function createAppTheme(mode: ThemeMode) {
  return createTheme({
    palette: {
      mode,
      primary: {
        main: mode === "light" ? "#3fbf73" : "#63d191",
      },
    },
    shape: {
      borderRadius: 10,
    },
  });
}
