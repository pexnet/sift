import type { ArticleListItem } from "../../../shared/types/contracts";

type ReadToggleDecision = {
  payload: { is_read: boolean };
  shouldAdvance: boolean;
};

export function getReadToggleDecision(selectedArticle: ArticleListItem | undefined): ReadToggleDecision | null {
  if (!selectedArticle) {
    return null;
  }

  const nextIsRead = !selectedArticle.is_read;
  return {
    payload: { is_read: nextIsRead },
    shouldAdvance: nextIsRead,
  };
}
