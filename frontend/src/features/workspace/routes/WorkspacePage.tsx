import { Stack } from "@mui/material";
import { useMemo, useRef } from "react";

import { findArticleById, getSelectedArticleId } from "../../../entities/article/model";
import { flattenNavigation } from "../../../entities/navigation/model";
import type { WorkspaceSearch } from "../../../shared/types/contracts";
import { ArticlesPane } from "../components/ArticlesPane";
import { DashboardRow } from "../components/DashboardRow";
import { NavigationPane } from "../components/NavigationPane";
import { ReaderPane } from "../components/ReaderPane";
import { usePatchArticleStateMutation, useArticleDetailQuery, useArticlesQuery, useNavigationQuery } from "../api/workspaceHooks";
import { useWorkspaceShortcuts } from "../hooks/useWorkspaceShortcuts";
import { buildDashboardCards } from "../lib/dashboard";

type WorkspacePageProps = {
  search: WorkspaceSearch;
  density: "compact" | "comfortable";
  themeMode: "light" | "dark";
  setDensity: (density: "compact" | "comfortable") => void;
  setThemeMode: (mode: "light" | "dark") => void;
  setSearch: (patch: Partial<WorkspaceSearch>) => void;
};

export function WorkspacePage({
  search,
  density,
  themeMode,
  setDensity,
  setThemeMode,
  setSearch,
}: WorkspacePageProps) {
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const navigationQuery = useNavigationQuery();
  const articlesQuery = useArticlesQuery(search);

  const articles = articlesQuery.data?.items ?? [];
  const selectedArticleId = getSelectedArticleId(articles, search.article_id);
  const selectedArticle = findArticleById(articles, selectedArticleId);

  const articleDetailQuery = useArticleDetailQuery(selectedArticleId);
  const patchArticleStateMutation = usePatchArticleStateMutation(selectedArticleId);

  const navItems = useMemo(() => {
    if (!navigationQuery.data) {
      return [];
    }
    return flattenNavigation(navigationQuery.data);
  }, [navigationQuery.data]);

  const selectedScopeKey = search.scope_type === "system" ? search.state : search.scope_id;
  const selectedNavItem = navItems.find((item) => item.scope_type === search.scope_type && item.scope_id === selectedScopeKey);
  const selectedScopeLabel =
    selectedNavItem?.scope_type === "folder"
      ? selectedNavItem.name
      : selectedNavItem?.scope_type === "stream"
        ? selectedNavItem.name
        : selectedNavItem?.title || "All articles";

  const dashboardCards = buildDashboardCards(navigationQuery.data, articles, selectedScopeLabel);

  const moveSelection = (delta: number) => {
    if (articles.length === 0) {
      return;
    }

    const currentIndex = Math.max(
      0,
      articles.findIndex((article) => article.id === selectedArticleId)
    );

    const nextIndex = Math.max(0, Math.min(articles.length - 1, currentIndex + delta));
    const nextArticle = articles[nextIndex];
    if (nextArticle) {
      setSearch({ article_id: nextArticle.id });
    }
  };

  const openSelection = () => {
    const firstArticle = articles[0];
    if (!search.article_id && firstArticle) {
      setSearch({ article_id: firstArticle.id });
    }
  };

  const toggleRead = () => {
    if (!selectedArticle) {
      return;
    }
    patchArticleStateMutation.mutate({ is_read: !selectedArticle.is_read });
  };

  const toggleSaved = () => {
    if (!selectedArticle) {
      return;
    }
    patchArticleStateMutation.mutate({ is_starred: !selectedArticle.is_starred });
  };

  useWorkspaceShortcuts({
    articleItems: articles,
    search,
    searchInputRef,
    selectedArticle,
    moveSelection,
    openSelection,
    toggleRead,
    toggleSaved,
  });

  return (
    <Stack spacing={2}>
      <DashboardRow cards={dashboardCards} />

      <Stack className={`react-workspace__grid react-density-${density}`} spacing={2}>
        <NavigationPane
          density={density}
          navItems={navItems}
          selectedScopeType={search.scope_type}
          selectedScopeKey={selectedScopeKey}
          isLoading={navigationQuery.isLoading}
          isError={navigationQuery.isError}
          onSelectItem={(item) => {
            if (item.scope_type === "system") {
              setSearch({
                scope_type: "system",
                scope_id: "",
                state: item.key,
                article_id: "",
              });
              return;
            }

            setSearch({
              scope_type: item.scope_type,
              scope_id: item.scope_id,
              article_id: "",
            });
          }}
          onToggleTheme={() => setThemeMode(themeMode === "dark" ? "light" : "dark")}
          themeMode={themeMode}
          onDensityChange={setDensity}
        />

        <ArticlesPane
          density={density}
          search={search}
          articleItems={articles}
          selectedArticleId={selectedArticleId}
          isLoading={articlesQuery.isLoading}
          isError={articlesQuery.isError}
          searchInputRef={searchInputRef}
          onSearchChange={(value) => setSearch({ q: value, article_id: "" })}
          onStateChange={(value) => setSearch({ state: value, article_id: "" })}
          onArticleSelect={(articleId) => setSearch({ article_id: articleId })}
        />

        <ReaderPane
          selectedArticle={selectedArticle}
          selectedArticleId={selectedArticleId}
          detail={articleDetailQuery.data}
          isLoading={articleDetailQuery.isLoading}
          isError={articleDetailQuery.isError}
          isMutating={patchArticleStateMutation.isPending}
          hasMutationError={patchArticleStateMutation.isError}
          onToggleRead={toggleRead}
          onToggleSaved={toggleSaved}
        />
      </Stack>
    </Stack>
  );
}
