import { NAV_FOLDERS_EXPANDED_KEY, NAV_MONITORING_EXPANDED_KEY, NAV_VISUAL_PRESET_KEY } from "../../../shared/lib/storage";

export type NavVisualPreset = "tight" | "balanced" | "airy";

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

export function loadExpandedFolderIds(): Set<string> | null {
  try {
    const storage = resolveStorage();
    if (!storage) {
      return null;
    }

    const raw = storage.getItem(NAV_FOLDERS_EXPANDED_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return null;
    }
    return new Set(
      parsed
        .map((value) => (typeof value === "string" ? value.trim() : ""))
        .filter((value) => value.length > 0)
    );
  } catch {
    return null;
  }
}

export function saveExpandedFolderIds(ids: Set<string>): void {
  const values = Array.from(ids).sort();
  const storage = resolveStorage();
  if (!storage) {
    return;
  }
  storage.setItem(NAV_FOLDERS_EXPANDED_KEY, JSON.stringify(values));
}

export function loadMonitoringExpanded(): boolean | null {
  try {
    const storage = resolveStorage();
    if (!storage) {
      return null;
    }

    const raw = storage.getItem(NAV_MONITORING_EXPANDED_KEY);
    if (raw === null) {
      return null;
    }

    if (raw === "true") {
      return true;
    }
    if (raw === "false") {
      return false;
    }
    return null;
  } catch {
    return null;
  }
}

export function saveMonitoringExpanded(value: boolean): void {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }
  storage.setItem(NAV_MONITORING_EXPANDED_KEY, value ? "true" : "false");
}

export function loadNavVisualPreset(): NavVisualPreset | null {
  try {
    const storage = resolveStorage();
    if (!storage) {
      return null;
    }

    const raw = storage.getItem(NAV_VISUAL_PRESET_KEY);
    if (!raw) {
      return null;
    }
    if (raw === "tight" || raw === "balanced" || raw === "airy") {
      return raw;
    }
    return null;
  } catch {
    return null;
  }
}

export function saveNavVisualPreset(value: NavVisualPreset): void {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }
  storage.setItem(NAV_VISUAL_PRESET_KEY, value);
}
