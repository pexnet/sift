import type { ComponentType } from "react";

import type { PluginArea } from "../../../shared/types/contracts";

type PluginAreaMountProps = {
  area: PluginArea;
};

export type PluginAreaRegistration = {
  id: string;
  title: string;
  mount: ComponentType<PluginAreaMountProps>;
  capabilities?: Record<string, boolean>;
};

export type PluginAreaRegistry = {
  ordered: PluginAreaRegistration[];
  byId: Record<string, PluginAreaRegistration>;
};

const OPTIONAL_CAPABILITY_KEYS = new Set(["supportsBadge", "supportsRefresh"]);

function sanitizeCapabilities(
  registration: PluginAreaRegistration,
  logger: Pick<Console, "debug">
): Record<string, boolean> {
  const rawCapabilities = registration.capabilities ?? {};
  const sanitized: Record<string, boolean> = {};
  for (const [key, value] of Object.entries(rawCapabilities)) {
    if (!OPTIONAL_CAPABILITY_KEYS.has(key)) {
      logger.debug("plugin.ui.registration.unknown_capability", {
        plugin_id: registration.id,
        capability: key,
      });
      continue;
    }
    sanitized[key] = Boolean(value);
  }
  return sanitized;
}

function isValidRegistration(
  registration: PluginAreaRegistration | null | undefined
): registration is PluginAreaRegistration {
  if (!registration) {
    return false;
  }
  if (registration.id.trim().length === 0) {
    return false;
  }
  if (registration.title.trim().length === 0) {
    return false;
  }
  return typeof registration.mount === "function";
}

export function createPluginAreaRegistry(
  registrations: Array<PluginAreaRegistration | null | undefined>,
  logger: Pick<Console, "debug"> = console
): PluginAreaRegistry {
  const ordered: PluginAreaRegistration[] = [];
  const byId: Record<string, PluginAreaRegistration> = {};

  for (const item of registrations) {
    if (!isValidRegistration(item)) {
      logger.debug("plugin.ui.registration.invalid", { registration: item });
      continue;
    }
    if (byId[item.id]) {
      logger.debug("plugin.ui.registration.duplicate", { plugin_id: item.id });
      continue;
    }
    const normalized: PluginAreaRegistration = {
      id: item.id,
      title: item.title,
      mount: item.mount,
      capabilities: sanitizeCapabilities(item, logger),
    };
    byId[item.id] = normalized;
    ordered.push(normalized);
  }

  return { ordered, byId };
}
