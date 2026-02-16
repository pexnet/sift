import { useEffect } from "react";
import type { MutableRefObject } from "react";

import type { ArticleListItem, WorkspaceSearch } from "../../../shared/types/contracts";

type UseWorkspaceShortcutsProps = {
  articleItems: ArticleListItem[];
  search: WorkspaceSearch;
  searchInputRef: MutableRefObject<HTMLInputElement | null>;
  selectedArticle: ArticleListItem | undefined;
  moveSelection: (delta: number) => void;
  openSelection: () => void;
  toggleRead: () => void;
  toggleSaved: () => void;
};

export function useWorkspaceShortcuts({
  articleItems,
  search,
  searchInputRef,
  selectedArticle,
  moveSelection,
  openSelection,
  toggleRead,
  toggleSaved,
}: UseWorkspaceShortcutsProps) {
  useEffect(() => {
    const getReaderScrollElement = (): HTMLElement | null =>
      document.querySelector<HTMLElement>(".workspace-reader");

    const scrollReaderByViewport = (delta: number) => {
      if (!selectedArticle) {
        return false;
      }
      const reader = getReaderScrollElement();
      if (!reader) {
        return false;
      }
      const step = Math.max(Math.floor(reader.clientHeight * 0.88), 240);
      reader.scrollBy({ top: step * delta, behavior: "auto" });
      return true;
    };

    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target;
      const isEditable =
        target instanceof HTMLElement &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

      if (isEditable || event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }

      if (event.key === "j") {
        event.preventDefault();
        moveSelection(1);
        return;
      }

      if (event.key === "k") {
        event.preventDefault();
        moveSelection(-1);
        return;
      }

      if (event.key === "o") {
        event.preventDefault();
        openSelection();
        return;
      }

      if (event.key === "m") {
        event.preventDefault();
        if (selectedArticle) {
          toggleRead();
        }
        return;
      }

      if (event.key === "s") {
        event.preventDefault();
        if (selectedArticle) {
          toggleSaved();
        }
        return;
      }

      if (event.key === "/") {
        event.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      if (event.key === "PageDown") {
        if (scrollReaderByViewport(1)) {
          event.preventDefault();
        }
        return;
      }

      if (event.key === "PageUp") {
        if (scrollReaderByViewport(-1)) {
          event.preventDefault();
        }
        return;
      }

      if (event.key === " ") {
        if (scrollReaderByViewport(event.shiftKey ? -1 : 1)) {
          event.preventDefault();
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    articleItems,
    moveSelection,
    openSelection,
    search.article_id,
    searchInputRef,
    selectedArticle,
    toggleRead,
    toggleSaved,
  ]);
}
