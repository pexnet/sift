import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DiscoveryStreamsPage } from "./DiscoveryStreamsPage";

const discoveryWorkbenchSpy = vi.fn<(props: { mode: "settings" | "workspace" }) => void>();

vi.mock("../components/DiscoveryWorkbench", () => ({
  DiscoveryWorkbench: ({ mode }: { mode: "settings" | "workspace" }) => {
    discoveryWorkbenchSpy({ mode });
    return <div data-testid="discovery-workbench">Discovery Workbench</div>;
  },
}));

describe("DiscoveryStreamsPage", () => {
  it("renders page scaffold and mounts discovery workbench in settings mode", () => {
    render(<DiscoveryStreamsPage />);

    expect(screen.getByRole("heading", { name: "Discover feeds" })).toBeVisible();
    expect(screen.getByText("Manage discovery streams, generate recommendations, and decide which feeds to add.")).toBeVisible();
    expect(screen.getByTestId("discovery-workbench")).toBeVisible();
    expect(discoveryWorkbenchSpy).toHaveBeenCalledWith({ mode: "settings" });
  });
});

