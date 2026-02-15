import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { clampPaneLayout, getDefaultPaneLayout, loadPaneLayout, savePaneLayout, type PaneLayout } from "../lib/paneLayout";

type SplitterTarget = "nav" | "list";

type DragState = {
  target: SplitterTarget;
  startX: number;
  startLayout: PaneLayout;
};

type UsePaneResizingOptions = {
  enabled: boolean;
};

type UsePaneResizingResult = {
  layout: PaneLayout;
  navSplitterProps: {
    role: "separator";
    tabIndex: number;
    "aria-orientation": "vertical";
    "aria-label": string;
    onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onKeyDown: (event: ReactKeyboardEvent<HTMLDivElement>) => void;
  };
  listSplitterProps: {
    role: "separator";
    tabIndex: number;
    "aria-orientation": "vertical";
    "aria-label": string;
    onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onKeyDown: (event: ReactKeyboardEvent<HTMLDivElement>) => void;
  };
  isNavDragging: boolean;
  isListDragging: boolean;
};

function getViewportWidth(): number {
  if (typeof window === "undefined") {
    return 1600;
  }
  return window.innerWidth || 1600;
}

export function usePaneResizing({ enabled }: UsePaneResizingOptions): UsePaneResizingResult {
  const [layout, setLayout] = useState<PaneLayout>(() => {
    const viewportWidth = getViewportWidth();
    return loadPaneLayout(viewportWidth) ?? getDefaultPaneLayout(viewportWidth);
  });
  const [dragTarget, setDragTarget] = useState<SplitterTarget | null>(null);
  const dragRef = useRef<DragState | null>(null);

  const updateClampedLayout = useCallback((next: PaneLayout) => {
    const viewportWidth = getViewportWidth();
    setLayout(clampPaneLayout(next, viewportWidth));
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const onResize = () => {
      setLayout((current) => clampPaneLayout(current, getViewportWidth()));
    };

    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [enabled]);

  const stopDragging = useCallback(() => {
    setDragTarget(null);
    dragRef.current = null;
    savePaneLayout(layout);
  }, [layout]);

  useEffect(() => {
    if (!enabled || !dragTarget) {
      return;
    }

    const onPointerMove = (event: globalThis.PointerEvent) => {
      const state = dragRef.current;
      if (!state) {
        return;
      }

      const delta = event.clientX - state.startX;
      if (state.target === "nav") {
        updateClampedLayout({
          navWidth: state.startLayout.navWidth + delta,
          listWidth: state.startLayout.listWidth,
        });
        return;
      }

      updateClampedLayout({
        navWidth: state.startLayout.navWidth,
        listWidth: state.startLayout.listWidth + delta,
      });
    };

    const onPointerUp = () => {
      stopDragging();
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, [dragTarget, enabled, stopDragging, updateClampedLayout]);

  const startDragging = useCallback(
    (target: SplitterTarget, event: ReactPointerEvent<HTMLDivElement>) => {
      if (!enabled) {
        return;
      }
      dragRef.current = {
        target,
        startX: event.clientX,
        startLayout: layout,
      };
      setDragTarget(target);
    },
    [enabled, layout]
  );

  const onSeparatorKeyDown = useCallback(
    (target: SplitterTarget, event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (!enabled) {
        return;
      }

      const largeStep = event.shiftKey ? 40 : 16;
      let next: PaneLayout | null = null;

      if (target === "nav") {
        if (event.key === "ArrowLeft") {
          next = { ...layout, navWidth: layout.navWidth - largeStep };
        } else if (event.key === "ArrowRight") {
          next = { ...layout, navWidth: layout.navWidth + largeStep };
        } else if (event.key === "Home") {
          next = { ...layout, navWidth: -Infinity };
        } else if (event.key === "End") {
          next = { ...layout, navWidth: Infinity };
        }
      } else if (event.key === "ArrowLeft") {
        next = { ...layout, listWidth: layout.listWidth - largeStep };
      } else if (event.key === "ArrowRight") {
        next = { ...layout, listWidth: layout.listWidth + largeStep };
      } else if (event.key === "Home") {
        next = { ...layout, listWidth: -Infinity };
      } else if (event.key === "End") {
        next = { ...layout, listWidth: Infinity };
      }

      if (!next) {
        return;
      }

      event.preventDefault();
      const clamped = clampPaneLayout(next, getViewportWidth());
      setLayout(clamped);
      savePaneLayout(clamped);
    },
    [enabled, layout]
  );

  const navSplitterProps = useMemo(
    () => ({
      role: "separator" as const,
      tabIndex: 0,
      "aria-orientation": "vertical" as const,
      "aria-label": "Resize navigation pane",
      onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => startDragging("nav", event),
      onKeyDown: (event: ReactKeyboardEvent<HTMLDivElement>) => onSeparatorKeyDown("nav", event),
    }),
    [onSeparatorKeyDown, startDragging]
  );

  const listSplitterProps = useMemo(
    () => ({
      role: "separator" as const,
      tabIndex: 0,
      "aria-orientation": "vertical" as const,
      "aria-label": "Resize reader pane",
      onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => startDragging("list", event),
      onKeyDown: (event: ReactKeyboardEvent<HTMLDivElement>) => onSeparatorKeyDown("list", event),
    }),
    [onSeparatorKeyDown, startDragging]
  );

  return {
    layout,
    navSplitterProps,
    listSplitterProps,
    isNavDragging: dragTarget === "nav",
    isListDragging: dragTarget === "list",
  };
}
