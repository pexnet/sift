import { beforeEach, describe, expect, it } from "vitest";

import { DENSITY_KEY, NAV_VISUAL_PRESET_KEY, THEME_KEY, UI_PREFERENCES_KEY } from "../shared/lib/storage";
import { DEFAULT_UI_PREFERENCES, loadUiPreferences, saveUiPreferences } from "./uiPreferences";

describe("uiPreferences", () => {
  const storage = window.localStorage;

  beforeEach(() => {
    storage.clear();
  });

  it("returns defaults when nothing is stored", () => {
    expect(loadUiPreferences()).toEqual(DEFAULT_UI_PREFERENCES);
  });

  it("loads legacy values when unified key is missing", () => {
    storage.setItem(THEME_KEY, "dark");
    storage.setItem(DENSITY_KEY, "comfortable");
    storage.setItem(NAV_VISUAL_PRESET_KEY, "airy");

    expect(loadUiPreferences()).toEqual({
      themeMode: "dark",
      themePreset: "classic",
      density: "comfortable",
      navPreset: "airy",
    });
  });

  it("loads unified preferences when key is present", () => {
    storage.setItem(
      UI_PREFERENCES_KEY,
      JSON.stringify({
        themeMode: "dark",
        themePreset: "graphite",
        density: "comfortable",
        navPreset: "tight",
      })
    );

    expect(loadUiPreferences()).toEqual({
      themeMode: "dark",
      themePreset: "graphite",
      density: "comfortable",
      navPreset: "tight",
    });
  });

  it("falls back invalid unified values to legacy/default values", () => {
    storage.setItem(THEME_KEY, "dark");
    storage.setItem(UI_PREFERENCES_KEY, JSON.stringify({ themeMode: "nope", themePreset: "oops" }));

    expect(loadUiPreferences()).toEqual({
      themeMode: "dark",
      themePreset: "classic",
      density: "compact",
      navPreset: "balanced",
    });
  });

  it("saves unified and legacy keys together", () => {
    const preferences = {
      themeMode: "dark",
      themePreset: "ocean",
      density: "comfortable",
      navPreset: "tight",
    } as const;

    saveUiPreferences(preferences);

    expect(storage.getItem(UI_PREFERENCES_KEY)).toBe(JSON.stringify(preferences));
    expect(storage.getItem(THEME_KEY)).toBe("dark");
    expect(storage.getItem(DENSITY_KEY)).toBe("comfortable");
    expect(storage.getItem(NAV_VISUAL_PRESET_KEY)).toBe("tight");
  });
});
