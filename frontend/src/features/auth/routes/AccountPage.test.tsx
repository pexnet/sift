import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { DENSITY_KEY, NAV_VISUAL_PRESET_KEY, THEME_KEY, UI_PREFERENCES_KEY } from "../../../shared/lib/storage";
import { useCurrentUser } from "../api/authHooks";
import { AccountPage } from "./AccountPage";

vi.mock("../api/authHooks", () => ({
  useCurrentUser: vi.fn(),
}));

const useCurrentUserMock = vi.mocked(useCurrentUser);

function renderPage() {
  return render(
    <AppProviders>
      <AccountPage />
    </AppProviders>
  );
}

function getStoredPreferences() {
  const raw = window.localStorage.getItem(UI_PREFERENCES_KEY);
  return raw ? (JSON.parse(raw) as Record<string, string>) : null;
}

describe("AccountPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useCurrentUserMock.mockReturnValue({
      isLoading: false,
      data: {
        id: "ef17c1a1-3b95-49ed-bf5c-c746e4ac3a20",
        email: "settings@example.com",
        display_name: "Settings User",
        is_admin: false,
      },
    } as ReturnType<typeof useCurrentUser>);
  });

  it("renders accessible settings groups and account identity summary", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Settings" })).toBeVisible();
    expect(screen.getByText("Theme mode", { selector: "legend" })).toBeVisible();
    expect(screen.getByText("Theme preset", { selector: "legend" })).toBeVisible();
    expect(screen.getByText("Density", { selector: "legend" })).toBeVisible();
    expect(screen.getByText("Navigation preset", { selector: "legend" })).toBeVisible();
    expect(screen.getByText("Use arrow keys to move options and Enter or Space to select.")).toBeVisible();

    expect(screen.getByText("settings@example.com")).toBeVisible();
    expect(screen.getByText("Settings User")).toBeVisible();
  });

  it("persists selected preferences from settings interactions", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Dark" }));
    fireEvent.click(screen.getByRole("button", { name: "Ocean Slate" }));
    fireEvent.click(screen.getByRole("button", { name: "Comfortable" }));
    fireEvent.click(screen.getByRole("button", { name: "Airy" }));

    await waitFor(() => {
      expect(getStoredPreferences()).toEqual({
        themeMode: "dark",
        themePreset: "ocean",
        density: "comfortable",
        navPreset: "airy",
      });
    });

    expect(window.localStorage.getItem(THEME_KEY)).toBe("dark");
    expect(window.localStorage.getItem(DENSITY_KEY)).toBe("comfortable");
    expect(window.localStorage.getItem(NAV_VISUAL_PRESET_KEY)).toBe("airy");
  });

  it("supports arrow-key selection movement in theme mode options", async () => {
    renderPage();

    const lightButton = screen.getByRole("button", { name: "Light" });
    const darkButton = screen.getByRole("button", { name: "Dark" });

    lightButton.focus();
    expect(lightButton).toHaveFocus();

    fireEvent.keyDown(lightButton, { key: "ArrowRight" });
    expect(darkButton).toHaveFocus();
    expect(darkButton).toHaveAttribute("aria-pressed", "true");

    await waitFor(() => {
      expect(getStoredPreferences()).toMatchObject({ themeMode: "dark" });
    });
  });
});
