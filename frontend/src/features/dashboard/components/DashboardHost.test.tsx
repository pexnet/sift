import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DashboardCardRegistration } from "./DashboardHost";
import { DashboardHost } from "./DashboardHost";

describe("DashboardHost", () => {
  it("renders loading and error states", () => {
    const { rerender } = render(<DashboardHost summary={undefined} isLoading isError={false} />);
    expect(screen.getByText("Loading dashboard…")).toBeVisible();

    rerender(<DashboardHost summary={undefined} isLoading={false} isError />);
    expect(screen.getByText("Failed to load dashboard summary.")).toBeVisible();
  });

  it("renders ready and unavailable cards deterministically", () => {
    render(
      <DashboardHost
        isLoading={false}
        isError={false}
        summary={{
          last_updated_at: new Date().toISOString(),
          cards: [
            {
              id: "saved_followup",
              title: "Saved follow-up",
              status: "ready",
            },
            {
              id: "trends",
              title: "Trends",
              status: "unavailable",
              reason: "Trends pipeline unavailable",
              dependency_spec: "docs/specs/trends-detection-dashboard-v1.md",
            },
          ],
        }}
      />
    );

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    expect(screen.getByText(/Saved follow-up data wiring is planned in the command-center data slice\./i)).toBeVisible();
    expect(screen.getByText("Trends pipeline unavailable")).toBeVisible();
    expect(screen.getByText("Dependency: docs/specs/trends-detection-dashboard-v1.md")).toBeVisible();
  });

  it("isolates ready-card render failures behind card unavailable fallback", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const throwingRegistry: Record<string, DashboardCardRegistration> = {
      saved_followup: {
        id: "saved_followup",
        title: "Saved follow-up",
        source: "plugin",
        mount: () => {
          throw new Error("card boom");
        },
      },
    };

    try {
      render(
        <DashboardHost
          isLoading={false}
          isError={false}
          registryById={throwingRegistry}
          summary={{
            last_updated_at: new Date().toISOString(),
            cards: [
              {
                id: "saved_followup",
                title: "Saved follow-up",
                status: "ready",
              },
            ],
          }}
        />
      );
      expect(screen.getByText("Card unavailable")).toBeVisible();
    } finally {
      consoleSpy.mockRestore();
    }
  });
});
