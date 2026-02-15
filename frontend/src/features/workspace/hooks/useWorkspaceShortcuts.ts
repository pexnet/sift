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
