import { beforeEach, describe, expect, it } from "vitest";

import { PANE_LAYOUT_KEY } from "../../../shared/lib/storage";
import { clampPaneLayout, getDefaultPaneLayout, loadPaneLayout, savePaneLayout } from "./paneLayout";

describe("paneLayout", () => {
  const storage = window.localStorage;

  beforeEach(() => {
    storage.clear();
  });

  it("loads persisted pane layout and clamps to viewport", () => {
    storage.setItem(PANE_LAYOUT_KEY, JSON.stringify({ navWidth: 300, listWidth: 500 }));
    const loaded = loadPaneLayout(1600);
    expect(loaded).toEqual({ navWidth: 300, listWidth: 500 });
  });

  it("returns null for malformed persisted values", () => {
    storage.setItem(PANE_LAYOUT_KEY, JSON.stringify({ navWidth: "bad", listWidth: 500 }));
    expect(loadPaneLayout(1600)).toBeNull();
  });

  it("saves deterministic integer payload", () => {
    savePaneLayout({ navWidth: 320.6, listWidth: 481.2 });
    expect(storage.getItem(PANE_LAYOUT_KEY)).toBe(JSON.stringify({ navWidth: 321, listWidth: 481 }));
  });

  it("clamps overly large widths", () => {
    const clamped = clampPaneLayout({ navWidth: 900, listWidth: 1400 }, 1700);
    expect(clamped.navWidth).toBeLessThanOrEqual(420);
    expect(clamped.listWidth).toBeLessThanOrEqual(980);
  });

  it("provides sensible defaults", () => {
    const layout = getDefaultPaneLayout(1700);
    expect(layout.navWidth).toBeGreaterThanOrEqual(240);
    expect(layout.listWidth).toBeGreaterThanOrEqual(360);
  });
});
