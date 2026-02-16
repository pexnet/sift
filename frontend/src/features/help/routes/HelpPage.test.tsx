import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppProviders } from "../../../app/providers";
import { HelpPage } from "./HelpPage";

describe("HelpPage", () => {
  it("renders monitoring setup and syntax reference content", () => {
    render(
      <AppProviders>
        <HelpPage />
      </AppProviders>
    );

    expect(screen.getByRole("heading", { name: "Help" })).toBeVisible();
    expect(screen.getByText("Configure a monitoring feed")).toBeVisible();
    expect(screen.getByText("Search query syntax (v1)")).toBeVisible();
    expect(screen.getByText("microsoft AND sentinel")).toBeVisible();
    expect(screen.getByRole("link", { name: "Open monitoring feeds" })).toHaveAttribute("href", "/account/monitoring");
  });
});
