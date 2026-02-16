import {
  DENSITY_KEY,
  NAV_VISUAL_PRESET_KEY,
  THEME_KEY,
  UI_PREFERENCES_KEY,
} from "../shared/lib/storage";

export type ThemeMode = "light" | "dark";
export type ThemePreset = "classic" | "ocean" | "graphite" | "sand";
export type DensityMode = "compact" | "comfortable";
export type NavVisualPreset = "tight" | "balanced" | "airy";

export type UiPreferences = {
  themeMode: ThemeMode;
  themePreset: ThemePreset;
  density: DensityMode;
  navPreset: NavVisualPreset;
};

export const DEFAULT_UI_PREFERENCES: UiPreferences = {
  themeMode: "light",
  themePreset: "classic",
  density: "compact",
  navPreset: "balanced",
};

export const THEME_PRESET_OPTIONS: ReadonlyArray<{ value: ThemePreset; label: string }> = [
  { value: "classic", label: "Sift Classic" },
  { value: "ocean", label: "Ocean Slate" },
  { value: "graphite", label: "Graphite Violet" },
  { value: "sand", label: "Warm Sand" },
];

export const NAV_PRESET_OPTIONS: ReadonlyArray<{ value: NavVisualPreset; label: string }> = [
  { value: "tight", label: "Tight" },
  { value: "balanced", label: "Balanced" },
  { value: "airy", label: "Airy" },
];

function resolveStorage(): Storage | null {
  if (typeof window !== "undefined" && typeof window.localStorage?.getItem === "function") {
    return window.localStorage;
  }

  const candidate = (globalThis as { localStorage?: unknown }).localStorage;
  if (
    candidate &&
    typeof candidate === "object" &&
    "getItem" in candidate &&
    typeof (candidate as Storage).getItem === "function" &&
    "setItem" in candidate &&
    typeof (candidate as Storage).setItem === "function"
  ) {
    return candidate as Storage;
  }

  return null;
}

function readLegacyDefaults(storage: Storage): UiPreferences {
  const themeMode: ThemeMode = storage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
  const density: DensityMode = storage.getItem(DENSITY_KEY) === "comfortable" ? "comfortable" : "compact";

  const navRaw = storage.getItem(NAV_VISUAL_PRESET_KEY);
  const navPreset: NavVisualPreset = navRaw === "tight" || navRaw === "airy" || navRaw === "balanced" ? navRaw : "balanced";

  return {
    ...DEFAULT_UI_PREFERENCES,
    themeMode,
    density,
    navPreset,
  };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function readThemeMode(value: unknown, fallback: ThemeMode): ThemeMode {
  return value === "dark" || value === "light" ? value : fallback;
}

function readThemePreset(value: unknown, fallback: ThemePreset): ThemePreset {
  return value === "classic" || value === "ocean" || value === "graphite" || value === "sand" ? value : fallback;
}

function readDensity(value: unknown, fallback: DensityMode): DensityMode {
  return value === "compact" || value === "comfortable" ? value : fallback;
}

function readNavPreset(value: unknown, fallback: NavVisualPreset): NavVisualPreset {
  return value === "tight" || value === "balanced" || value === "airy" ? value : fallback;
}

export function loadUiPreferences(): UiPreferences {
  try {
    const storage = resolveStorage();
    if (!storage) {
      return DEFAULT_UI_PREFERENCES;
    }

    const legacyDefaults = readLegacyDefaults(storage);
    const raw = storage.getItem(UI_PREFERENCES_KEY);
    if (!raw) {
      return legacyDefaults;
    }

    const parsed = asRecord(JSON.parse(raw));
    if (!parsed) {
      return legacyDefaults;
    }

    return {
      themeMode: readThemeMode(parsed.themeMode, legacyDefaults.themeMode),
      themePreset: readThemePreset(parsed.themePreset, legacyDefaults.themePreset),
      density: readDensity(parsed.density, legacyDefaults.density),
      navPreset: readNavPreset(parsed.navPreset, legacyDefaults.navPreset),
    };
  } catch {
    return DEFAULT_UI_PREFERENCES;
  }
}

export function saveUiPreferences(preferences: UiPreferences): void {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }

  storage.setItem(UI_PREFERENCES_KEY, JSON.stringify(preferences));

  // Keep legacy keys in sync for backward compatibility.
  storage.setItem(THEME_KEY, preferences.themeMode);
  storage.setItem(DENSITY_KEY, preferences.density);
  storage.setItem(NAV_VISUAL_PRESET_KEY, preferences.navPreset);
}
