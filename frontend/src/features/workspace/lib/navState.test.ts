import { beforeEach, describe, expect, it } from "vitest";

import { NAV_FOLDERS_EXPANDED_KEY, NAV_MONITORING_EXPANDED_KEY, NAV_VISUAL_PRESET_KEY } from "../../../shared/lib/storage";
import {
  loadExpandedFolderIds,
  loadNavVisualPreset,
  loadMonitoringExpanded,
  saveExpandedFolderIds,
  saveNavVisualPreset,
  saveMonitoringExpanded,
} from "./navState";

describe("navState", () => {
  const storage = window.localStorage;

  beforeEach(() => {
    storage.clear();
  });

  it("loads persisted expanded folder ids", () => {
    storage.setItem(NAV_FOLDERS_EXPANDED_KEY, JSON.stringify(["a", "b"]));

    const loaded = loadExpandedFolderIds();
    expect(Array.from(loaded ?? [])).toEqual(["a", "b"]);
  });

  it("returns null on malformed data", () => {
    storage.setItem(NAV_FOLDERS_EXPANDED_KEY, "{oops");
    expect(loadExpandedFolderIds()).toBeNull();
  });

  it("saves ids deterministically", () => {
    saveExpandedFolderIds(new Set(["z", "a"]));
    expect(storage.getItem(NAV_FOLDERS_EXPANDED_KEY)).toBe(JSON.stringify(["a", "z"]));
  });

  it("loads persisted monitoring expansion preference", () => {
    storage.setItem(NAV_MONITORING_EXPANDED_KEY, "false");
    expect(loadMonitoringExpanded()).toBe(false);
  });

  it("returns null for invalid monitoring expansion value", () => {
    storage.setItem(NAV_MONITORING_EXPANDED_KEY, "maybe");
    expect(loadMonitoringExpanded()).toBeNull();
  });

  it("saves monitoring expansion preference", () => {
    saveMonitoringExpanded(true);
    expect(storage.getItem(NAV_MONITORING_EXPANDED_KEY)).toBe("true");
  });

  it("loads persisted nav visual preset", () => {
    storage.setItem(NAV_VISUAL_PRESET_KEY, "tight");
    expect(loadNavVisualPreset()).toBe("tight");
  });

  it("returns null for invalid nav visual preset", () => {
    storage.setItem(NAV_VISUAL_PRESET_KEY, "wide");
    expect(loadNavVisualPreset()).toBeNull();
  });

  it("saves nav visual preset", () => {
    saveNavVisualPreset("airy");
    expect(storage.getItem(NAV_VISUAL_PRESET_KEY)).toBe("airy");
  });
});
