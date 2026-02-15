import { beforeEach, describe, expect, it } from "vitest";

import { NAV_FOLDERS_EXPANDED_KEY, NAV_MONITORING_EXPANDED_KEY } from "../../../shared/lib/storage";
import {
  loadExpandedFolderIds,
  loadMonitoringExpanded,
  saveExpandedFolderIds,
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
});
