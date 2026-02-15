import BookmarkBorderRoundedIcon from "@mui/icons-material/BookmarkBorderRounded";
import RssFeedRoundedIcon from "@mui/icons-material/RssFeedRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SpaceDashboardRoundedIcon from "@mui/icons-material/SpaceDashboardRounded";
import { Box, Drawer, useMediaQuery } from "@mui/material";
import { useMemo, useRef, useState } from "react";

import { findArticleById, getSelectedArticleId } from "../../../entities/article/model";
import { getScopeLabel, toNavigationHierarchy } from "../../../entities/navigation/model";
import type { WorkspaceSearch } from "../../../shared/types/contracts";
import { ArticlesPane } from "../components/ArticlesPane";
import { NavigationPane } from "../components/NavigationPane";
import { ReaderPane } from "../components/ReaderPane";
import { WorkspaceRail } from "../components/WorkspaceRail";
import {
  useArticleDetailQuery,
  useArticlesQuery,
  useAssignFeedFolderMutation,
  useCreateFolderMutation,
  useDeleteFolderMutation,
  useFoldersQuery,
  useNavigationQuery,
  usePatchArticleStateMutation,
  useUpdateFolderMutation,
} from "../api/workspaceHooks";
import { useWorkspaceShortcuts } from "../hooks/useWorkspaceShortcuts";
import { toCreateFolderRequest, toFeedFolderAssignmentRequest, toUpdateFolderRequest } from "../lib/folderForms";
import { toReaderHtml } from "../lib/readerContent";

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
  const [isNavOpen, setIsNavOpen] = useState(false);
  const isTabletOrMobile = useMediaQuery("(max-width: 980px)");
  const isMobile = useMediaQuery("(max-width: 760px)");

  const navigationQuery = useNavigationQuery();
  const foldersQuery = useFoldersQuery();
  const hierarchy = useMemo(
    () => (navigationQuery.data ? toNavigationHierarchy(navigationQuery.data) : null),
    [navigationQuery.data]
  );

  const articlesQuery = useArticlesQuery(search);
  const articles = articlesQuery.data?.items ?? [];

  const selectedArticleId = getSelectedArticleId(articles, search.article_id);
  const selectedArticle = findArticleById(articles, selectedArticleId);

  const articleDetailQuery = useArticleDetailQuery(selectedArticleId);
  const readerContentHtml = useMemo(
    () => toReaderHtml(articleDetailQuery.data?.content_text ?? ""),
    [articleDetailQuery.data?.content_text]
  );
  const patchArticleStateMutation = usePatchArticleStateMutation(selectedArticleId);
  const createFolderMutation = useCreateFolderMutation();
  const updateFolderMutation = useUpdateFolderMutation();
  const deleteFolderMutation = useDeleteFolderMutation();
  const assignFeedFolderMutation = useAssignFeedFolderMutation();

  const selectedScopeKey = search.scope_type === "system" ? search.state : search.scope_id;
  const selectedScopeLabel = hierarchy
    ? getScopeLabel(hierarchy, search.scope_type, search.scope_id, search.state)
    : "All articles";

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

  const systemAllCount = hierarchy?.systems.find((system) => system.scope_id === "all")?.unread_count ?? 0;
  const systemSavedCount = hierarchy?.systems.find((system) => system.scope_id === "saved")?.unread_count ?? 0;
  const navOpen = isTabletOrMobile && isNavOpen;
  const showArticlesPane = !isMobile || !selectedArticleId;
  const showReaderPane = !isMobile || Boolean(selectedArticleId);

  const navigationPane = (
    <NavigationPane
      density={density}
      hierarchy={hierarchy}
      folders={foldersQuery.data ?? []}
      selectedScopeType={search.scope_type}
      selectedScopeKey={selectedScopeKey}
      isLoading={navigationQuery.isLoading}
      isError={navigationQuery.isError}
      onSelectSystem={(systemKey) => {
        setSearch({
          scope_type: "system",
          scope_id: "",
          state: systemKey as WorkspaceSearch["state"],
          article_id: "",
        });
        setIsNavOpen(false);
      }}
      onSelectFolder={(folderId) => {
        setSearch({
          scope_type: "folder",
          scope_id: folderId,
          article_id: "",
        });
        setIsNavOpen(false);
      }}
      onSelectFeed={(feedId) => {
        setSearch({
          scope_type: "feed",
          scope_id: feedId,
          article_id: "",
        });
        setIsNavOpen(false);
      }}
      onSelectStream={(streamId) => {
        setSearch({
          scope_type: "stream",
          scope_id: streamId,
          article_id: "",
        });
        setIsNavOpen(false);
      }}
      onCreateFolder={async (name) => {
        await createFolderMutation.mutateAsync(toCreateFolderRequest(name));
      }}
      onRenameFolder={async (folderId, name) => {
        await updateFolderMutation.mutateAsync({ folderId, payload: toUpdateFolderRequest(name) });
      }}
      onDeleteFolder={async (folderId) => {
        await deleteFolderMutation.mutateAsync(folderId);
        if (search.scope_type === "folder" && search.scope_id === folderId) {
          setSearch({ scope_type: "system", scope_id: "", state: "all", article_id: "" });
        }
      }}
      onAssignFeedFolder={async (feedId, folderId) => {
        await assignFeedFolderMutation.mutateAsync({
          feedId,
          payload: toFeedFolderAssignmentRequest(folderId),
        });
      }}
      isFolderMutationPending={createFolderMutation.isPending || updateFolderMutation.isPending || deleteFolderMutation.isPending}
      isAssignPending={assignFeedFolderMutation.isPending}
      onToggleTheme={() => setThemeMode(themeMode === "dark" ? "light" : "dark")}
      themeMode={themeMode}
      onDensityChange={setDensity}
    />
  );

  return (
    <Box className={`workspace-shell react-density-${density}`}>
      <WorkspaceRail
        actions={[
          {
            id: "dashboard",
            label: "Dashboard",
            icon: <SpaceDashboardRoundedIcon fontSize="small" />,
            onClick: () => setSearch({ scope_type: "system", scope_id: "", state: "all", article_id: "" }),
          },
          {
            id: "feeds",
            label: isTabletOrMobile ? "Nav" : "Feeds",
            icon: <RssFeedRoundedIcon fontSize="small" />,
            badge: systemAllCount,
            active: isTabletOrMobile
              ? navOpen
              : search.scope_type !== "system" || search.state === "all",
            onClick: () => {
              if (isTabletOrMobile) {
                setIsNavOpen((previous) => !previous);
                return;
              }
              setSearch({ scope_type: "system", scope_id: "", state: "all", article_id: "" });
            },
          },
          {
            id: "saved",
            label: "Saved",
            icon: <BookmarkBorderRoundedIcon fontSize="small" />,
            badge: systemSavedCount,
            active: search.scope_type === "system" && search.state === "saved",
            onClick: () => setSearch({ scope_type: "system", scope_id: "", state: "saved", article_id: "" }),
          },
          {
            id: "search",
            label: "Search",
            icon: <SearchRoundedIcon fontSize="small" />,
            onClick: () => searchInputRef.current?.focus(),
          },
        ]}
      />

      {isTabletOrMobile ? (
        <Drawer open={navOpen} onClose={() => setIsNavOpen(false)} PaperProps={{ className: "workspace-nav-drawer" }}>
          {navigationPane}
        </Drawer>
      ) : (
        navigationPane
      )}

      <Box className="workspace-content">
        {showArticlesPane ? (
          <ArticlesPane
            density={density}
            search={search}
            scopeLabel={selectedScopeLabel}
            articleItems={articles}
            selectedArticleId={selectedArticleId}
            isLoading={articlesQuery.isLoading}
            isError={articlesQuery.isError}
            searchInputRef={searchInputRef}
            onSearchChange={(value) => setSearch({ q: value, article_id: "" })}
            onStateChange={(value) => setSearch({ state: value, article_id: "" })}
            onArticleSelect={(articleId) => setSearch({ article_id: articleId })}
          />
        ) : null}

        {showReaderPane ? (
          <ReaderPane
            selectedArticle={selectedArticle}
            selectedArticleId={selectedArticleId}
            detail={articleDetailQuery.data}
            contentHtml={readerContentHtml}
            isLoading={articleDetailQuery.isLoading}
            isError={articleDetailQuery.isError}
            isMutating={patchArticleStateMutation.isPending}
            hasMutationError={patchArticleStateMutation.isError}
            onToggleRead={toggleRead}
            onToggleSaved={toggleSaved}
            onOpenOriginal={() => {
              const targetUrl = articleDetailQuery.data?.canonical_url ?? selectedArticle?.canonical_url;
              if (targetUrl) {
                window.open(targetUrl, "_blank", "noopener,noreferrer");
              }
            }}
            onMoveSelection={moveSelection}
            {...(isMobile
              ? {
                  onBackToList: () => setSearch({ article_id: "" }),
                }
              : {})}
          />
        ) : null}
      </Box>
    </Box>
  );
}
