import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PluginArea } from "../../../shared/types/contracts";
import type { PluginAreaRegistration } from "./registry";
import { PluginAreaHost } from "./PluginAreaHost";

const discoverArea: PluginArea = {
  id: "discover_feeds",
  title: "Discover feeds",
  icon: "search",
  order: 10,
  route_key: "discover-feeds",
};

describe("PluginAreaHost", () => {
  it("renders unavailable fallback when no registration exists", () => {
    render(<PluginAreaHost area={{ ...discoverArea, id: "missing_plugin" }} registryById={{}} />);
    expect(screen.getByText(/enabled but no frontend registration is available/i)).toBeVisible();
  });

  it("isolates render failures with plugin unavailable fallback", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const throwingRegistration: PluginAreaRegistration = {
      id: "discover_feeds",
      title: "Discover feeds",
      mount: () => {
        throw new Error("boom");
      },
      capabilities: {},
    };

    try {
      render(
        <PluginAreaHost
          area={discoverArea}
          registryById={{
            discover_feeds: throwingRegistration,
          }}
        />
      );
      expect(screen.getByText("Plugin unavailable")).toBeVisible();
    } finally {
      consoleSpy.mockRestore();
    }
  });
});
