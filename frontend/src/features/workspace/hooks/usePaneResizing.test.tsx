import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { PANE_LAYOUT_KEY } from "../../../shared/lib/storage";
import { usePaneResizing } from "./usePaneResizing";

function PaneResizingHarness() {
  const { layout, navSplitterProps, listSplitterProps } = usePaneResizing({ enabled: true });
  return (
    <div>
      <output data-testid="layout">{`${layout.navWidth}:${layout.listWidth}`}</output>
      <div data-testid="nav-splitter" {...navSplitterProps} />
      <div data-testid="list-splitter" {...listSplitterProps} />
    </div>
  );
}

describe("usePaneResizing", () => {
  const storage = window.localStorage;

  beforeEach(() => {
    storage.clear();
    Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: 1700 });
  });

  it("updates nav width by keyboard and persists layout", () => {
    render(<PaneResizingHarness />);

    const before = screen.getByTestId("layout").textContent ?? "";
    const navWidthBefore = Number(before.split(":")[0]);

    fireEvent.keyDown(screen.getByTestId("nav-splitter"), { key: "ArrowRight" });
    const after = screen.getByTestId("layout").textContent ?? "";
    const navWidthAfter = Number(after.split(":")[0]);

    expect(navWidthAfter).toBeGreaterThan(navWidthBefore);
    expect(storage.getItem(PANE_LAYOUT_KEY)).toBeTruthy();
  });

  it("updates list width by drag and persists on pointer up", () => {
    render(<PaneResizingHarness />);

    const before = screen.getByTestId("layout").textContent ?? "";
    const listWidthBefore = Number(before.split(":")[1]);

    fireEvent.pointerDown(screen.getByTestId("list-splitter"), { clientX: 500 });
    fireEvent.pointerMove(window, { clientX: 560 });
    fireEvent.pointerUp(window);

    const after = screen.getByTestId("layout").textContent ?? "";
    const listWidthAfter = Number(after.split(":")[1]);

    expect(listWidthAfter).toBeGreaterThan(listWidthBefore);
    expect(storage.getItem(PANE_LAYOUT_KEY)).toBeTruthy();
  });
});
