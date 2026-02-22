import { describe, expect, it, vi } from "vitest";

import { createPluginAreaRegistry, type PluginAreaRegistration } from "./registry";

function TestMount() {
  return null;
}

describe("plugin area registry", () => {
  it("keeps first registration on duplicate ids", () => {
    const logger = { debug: vi.fn() };
    const first: PluginAreaRegistration = { id: "dup", title: "One", mount: TestMount };
    const second: PluginAreaRegistration = { id: "dup", title: "Two", mount: TestMount };

    const registry = createPluginAreaRegistry([first, second], logger);

    expect(registry.ordered).toHaveLength(1);
    expect(registry.byId.dup?.title).toBe("One");
    expect(logger.debug).toHaveBeenCalledWith("plugin.ui.registration.duplicate", { plugin_id: "dup" });
  });

  it("skips invalid registrations and ignores unknown capability flags", () => {
    const logger = { debug: vi.fn() };

    const registry = createPluginAreaRegistry(
      [
        null,
        { id: "", title: "Invalid", mount: TestMount },
        {
          id: "discover_feeds",
          title: "Discover feeds",
          mount: TestMount,
          capabilities: {
            supportsBadge: true,
            unknownCapability: true,
          },
        },
      ],
      logger
    );

    expect(registry.ordered).toHaveLength(1);
    expect(registry.byId.discover_feeds?.capabilities).toEqual({ supportsBadge: true });
    expect(logger.debug).toHaveBeenCalledWith("plugin.ui.registration.unknown_capability", {
      plugin_id: "discover_feeds",
      capability: "unknownCapability",
    });
  });
});
