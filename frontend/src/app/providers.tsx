import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { DENSITY_KEY, THEME_KEY } from "../shared/lib/storage";
import { createAppTheme } from "./theme";

export type DensityMode = "compact" | "comfortable";

export type AppUiState = {
  density: DensityMode;
  setDensity: (density: DensityMode) => void;
  themeMode: "light" | "dark";
  setThemeMode: (themeMode: "light" | "dark") => void;
};

const AppUiStateContext = createContext<AppUiState | null>(null);
export const queryClient = new QueryClient();

function getStoredTheme(): "light" | "dark" {
  return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
}

function getStoredDensity(): DensityMode {
  return localStorage.getItem(DENSITY_KEY) === "comfortable" ? "comfortable" : "compact";
}

export function useAppUiState(): AppUiState {
  const value = useContext(AppUiStateContext);
  if (!value) {
    throw new Error("App UI state context is not available");
  }

  return value;
}

type AppProvidersProps = {
  children: ReactNode;
};

export function AppProviders({ children }: AppProvidersProps) {
  const [themeMode, setThemeModeState] = useState<"light" | "dark">(getStoredTheme);
  const [density, setDensityState] = useState<DensityMode>(getStoredDensity);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", themeMode);
    localStorage.setItem(THEME_KEY, themeMode);
  }, [themeMode]);

  useEffect(() => {
    localStorage.setItem(DENSITY_KEY, density);
  }, [density]);

  const theme = useMemo(() => createAppTheme(themeMode), [themeMode]);

  const uiState = useMemo<AppUiState>(
    () => ({
      density,
      setDensity: setDensityState,
      themeMode,
      setThemeMode: setThemeModeState,
    }),
    [density, themeMode]
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AppUiStateContext.Provider value={uiState}>{children}</AppUiStateContext.Provider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
