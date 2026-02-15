import { PANE_LAYOUT_KEY } from "../../../shared/lib/storage";

export type PaneLayout = {
  navWidth: number;
  listWidth: number;
};

export const WORKSPACE_RAIL_WIDTH = 76;
export const WORKSPACE_SPLITTER_WIDTH = 8;
export const NAV_WIDTH_MIN = 240;
export const NAV_WIDTH_MAX = 420;
export const LIST_WIDTH_MIN = 360;
export const LIST_WIDTH_MAX = 980;
export const READER_WIDTH_MIN = 420;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

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

function getAvailableWorkspaceWidth(viewportWidth: number): number {
  return Math.max(0, viewportWidth - WORKSPACE_RAIL_WIDTH - WORKSPACE_SPLITTER_WIDTH * 2);
}

function getEffectiveMinWidths(availableWorkspaceWidth: number): {
  navMin: number;
  listMin: number;
  readerMin: number;
} {
  const requestedTotal = NAV_WIDTH_MIN + LIST_WIDTH_MIN + READER_WIDTH_MIN;
  if (availableWorkspaceWidth >= requestedTotal) {
    return { navMin: NAV_WIDTH_MIN, listMin: LIST_WIDTH_MIN, readerMin: READER_WIDTH_MIN };
  }

  const scale = requestedTotal > 0 ? availableWorkspaceWidth / requestedTotal : 1;
  let navMin = Math.max(180, Math.floor(NAV_WIDTH_MIN * scale));
  let listMin = Math.max(260, Math.floor(LIST_WIDTH_MIN * scale));
  let readerMin = Math.max(280, Math.floor(READER_WIDTH_MIN * scale));

  const overflow = navMin + listMin + readerMin - availableWorkspaceWidth;
  if (overflow > 0) {
    const listReducible = Math.max(0, listMin - 220);
    const listReduction = Math.min(listReducible, overflow);
    listMin -= listReduction;

    const overflowAfterList = overflow - listReduction;
    if (overflowAfterList > 0) {
      const readerReducible = Math.max(0, readerMin - 240);
      const readerReduction = Math.min(readerReducible, overflowAfterList);
      readerMin -= readerReduction;

      const overflowAfterReader = overflowAfterList - readerReduction;
      if (overflowAfterReader > 0) {
        navMin = Math.max(160, navMin - overflowAfterReader);
      }
    }
  }

  return { navMin, listMin, readerMin };
}

export function clampPaneLayout(layout: PaneLayout, viewportWidth: number): PaneLayout {
  const availableWorkspaceWidth = getAvailableWorkspaceWidth(viewportWidth);
  const { navMin, listMin, readerMin } = getEffectiveMinWidths(availableWorkspaceWidth);

  const navMaxByViewport = availableWorkspaceWidth - listMin - readerMin;
  const navMax = Math.max(navMin, Math.min(NAV_WIDTH_MAX, navMaxByViewport));
  const navWidth = clamp(Math.round(layout.navWidth), navMin, navMax);

  const listMaxByViewport = availableWorkspaceWidth - navWidth - readerMin;
  const listMax = Math.max(listMin, Math.min(LIST_WIDTH_MAX, listMaxByViewport));
  const listWidth = clamp(Math.round(layout.listWidth), listMin, listMax);

  return { navWidth, listWidth };
}

export function getDefaultPaneLayout(viewportWidth: number): PaneLayout {
  const availableWorkspaceWidth = getAvailableWorkspaceWidth(viewportWidth);
  const candidate: PaneLayout = {
    navWidth: 320,
    listWidth: Math.round(Math.max(0, availableWorkspaceWidth - 320) * 0.46),
  };
  return clampPaneLayout(candidate, viewportWidth);
}

export function loadPaneLayout(viewportWidth: number): PaneLayout | null {
  try {
    const storage = resolveStorage();
    if (!storage) {
      return null;
    }

    const raw = storage.getItem(PANE_LAYOUT_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return null;
    }

    const navWidth = Number((parsed as { navWidth?: unknown }).navWidth);
    const listWidth = Number((parsed as { listWidth?: unknown }).listWidth);
    if (!Number.isFinite(navWidth) || !Number.isFinite(listWidth)) {
      return null;
    }

    return clampPaneLayout({ navWidth, listWidth }, viewportWidth);
  } catch {
    return null;
  }
}

export function savePaneLayout(layout: PaneLayout): void {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }

  storage.setItem(
    PANE_LAYOUT_KEY,
    JSON.stringify({
      navWidth: Math.round(layout.navWidth),
      listWidth: Math.round(layout.listWidth),
    })
  );
}
