import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { createAppTheme } from "./theme";
import {
  DEFAULT_UI_PREFERENCES,
  loadUiPreferences,
  saveUiPreferences,
  type DensityMode,
  type NavVisualPreset,
  type ThemeMode,
  type ThemePreset,
} from "./uiPreferences";

export type AppUiState = {
  density: DensityMode;
  setDensity: (density: DensityMode) => void;
  navPreset: NavVisualPreset;
  setNavPreset: (navPreset: NavVisualPreset) => void;
  resetUiPreferences: () => void;
  themeMode: ThemeMode;
  setThemeMode: (themeMode: ThemeMode) => void;
  themePreset: ThemePreset;
  setThemePreset: (themePreset: ThemePreset) => void;
};

const AppUiStateContext = createContext<AppUiState | null>(null);
export const queryClient = new QueryClient();

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
  const [uiPreferences, setUiPreferences] = useState(loadUiPreferences);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", uiPreferences.themeMode);
    document.documentElement.setAttribute("data-theme-preset", uiPreferences.themePreset);
    saveUiPreferences(uiPreferences);
  }, [uiPreferences]);

  const theme = useMemo(
    () => createAppTheme(uiPreferences.themeMode, uiPreferences.themePreset),
    [uiPreferences.themeMode, uiPreferences.themePreset]
  );

  const uiState = useMemo<AppUiState>(
    () => ({
      density: uiPreferences.density,
      setDensity: (density) => setUiPreferences((previous) => ({ ...previous, density })),
      navPreset: uiPreferences.navPreset,
      setNavPreset: (navPreset) => setUiPreferences((previous) => ({ ...previous, navPreset })),
      resetUiPreferences: () => setUiPreferences({ ...DEFAULT_UI_PREFERENCES }),
      themeMode: uiPreferences.themeMode,
      setThemeMode: (themeMode) => setUiPreferences((previous) => ({ ...previous, themeMode })),
      themePreset: uiPreferences.themePreset,
      setThemePreset: (themePreset) => setUiPreferences((previous) => ({ ...previous, themePreset })),
    }),
    [uiPreferences]
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
