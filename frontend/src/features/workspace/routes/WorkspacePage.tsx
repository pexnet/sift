import BookmarkBorderRoundedIcon from "@mui/icons-material/BookmarkBorderRounded";
import DarkModeRoundedIcon from "@mui/icons-material/DarkModeRounded";
import HelpOutlineRoundedIcon from "@mui/icons-material/HelpOutlineRounded";
import LightModeRoundedIcon from "@mui/icons-material/LightModeRounded";
import RssFeedRoundedIcon from "@mui/icons-material/RssFeedRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import SpaceDashboardRoundedIcon from "@mui/icons-material/SpaceDashboardRounded";
import { useNavigate } from "@tanstack/react-router";
import { Alert, Box, Drawer, useMediaQuery } from "@mui/material";
import { useMemo, useRef, useState, type CSSProperties } from "react";

import { findArticleById, getSelectedArticleId } from "../../../entities/article/model";
import { getScopeLabel, toNavigationHierarchy } from "../../../entities/navigation/model";
import type { WorkspaceSearch } from "../../../shared/types/contracts";
import { DashboardHost } from "../../dashboard/components/DashboardHost";
import { PluginAreaHost } from "../plugins/PluginAreaHost";
import { ArticlesPane } from "../components/ArticlesPane";
import { NavigationPane } from "../components/NavigationPane";
import { ReaderPane } from "../components/ReaderPane";
import { WorkspaceRail } from "../components/WorkspaceRail";
import {
  useArticleDetailQuery,
  useArticlesQuery,
  useAssignFeedFolderMutation,
  useCreateFeedMutation,
  useCreateFolderMutation,
  useDeleteFolderMutation,
  useDashboardSummaryQuery,
  useFeedsQuery,
  useFetchArticleFulltextMutation,
  useFoldersQuery,
  useMarkScopeAsReadMutation,
  useNavigationQuery,
  usePluginAreasQuery,
  usePatchArticleStateMutation,
  useUpdateFolderMutation,
} from "../api/workspaceHooks";
import { getFeedIconUrl } from "../lib/feedIcons";
import { useWorkspaceShortcuts } from "../hooks/useWorkspaceShortcuts";
import { toCreateFolderRequest, toFeedFolderAssignmentRequest, toUpdateFolderRequest } from "../lib/folderForms";
import { getReadToggleDecision } from "../lib/readActions";
import { toReaderHtml } from "../lib/readerContent";
import { usePaneResizing } from "../hooks/usePaneResizing";

type WorkspacePageProps = {
  search: WorkspaceSearch;
  density: "compact" | "comfortable";
  navPreset: "tight" | "balanced" | "airy";
  themeMode: "light" | "dark";
  setThemeMode: (mode: "light" | "dark") => void;
  setSearch: (patch: Partial<WorkspaceSearch>) => void;
  activePluginAreaRouteKey?: string | null;
  activeDashboard?: boolean;
};

type WorkspaceLayoutMode = "desktop" | "tablet" | "mobile";
type MobilePaneState = "nav" | "list" | "reader";

export function WorkspacePage({
  search,
  density,
  navPreset,
  themeMode,
  setThemeMode,
  setSearch,
  activePluginAreaRouteKey = null,
  activeDashboard = false,
}: WorkspacePageProps) {
  const navigate = useNavigate();
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const [isNavOpen, setIsNavOpen] = useState(false);
  const isMobile = useMediaQuery("(max-width: 760px)");
  const isTablet = useMediaQuery("(max-width: 1200px)");
  const layoutMode: WorkspaceLayoutMode = isMobile ? "mobile" : isTablet ? "tablet" : "desktop";
  const usesDrawerNav = layoutMode !== "desktop";
  const {
    layout,
    navSplitterProps,
    listSplitterProps,
    isNavDragging,
    isListDragging,
  } = usePaneResizing({ enabled: layoutMode === "desktop" });

  const navigationQuery = useNavigationQuery();
  const pluginAreasQuery = usePluginAreasQuery();
  const dashboardSummaryQuery = useDashboardSummaryQuery(activeDashboard);
  const foldersQuery = useFoldersQuery();
  const feedsQuery = useFeedsQuery();
  const pluginAreas = pluginAreasQuery.data ?? [];
  const isDashboardView = activeDashboard;
  const isPluginAreaView = activePluginAreaRouteKey !== null && activePluginAreaRouteKey.length > 0;
  const activePluginArea = pluginAreas.find((pluginArea) => pluginArea.route_key === activePluginAreaRouteKey) ?? null;
  const hierarchy = useMemo(
    () => (navigationQuery.data ? toNavigationHierarchy(navigationQuery.data) : null),
    [navigationQuery.data]
  );
  const streamNameById = useMemo<Record<string, string>>(() => {
    const mapping: Record<string, string> = {};
    for (const stream of hierarchy?.streams ?? []) {
      mapping[stream.scope_id] = stream.name;
    }
    return mapping;
  }, [hierarchy]);
  const feedIconByFeedId = useMemo<Record<string, string | null>>(() => {
    const mapping: Record<string, string | null> = {};
    for (const feed of feedsQuery.data ?? []) {
      mapping[feed.id] = getFeedIconUrl(feed);
    }
    return mapping;
  }, [feedsQuery.data]);

  const contentIsContextView = isDashboardView || isPluginAreaView;
  const articlesQuery = useArticlesQuery(search, !contentIsContextView);
  const articles = articlesQuery.data?.items ?? [];

  const inferredSelectedArticleId = getSelectedArticleId(articles, search.article_id);
  const selectedArticleId =
    layoutMode === "mobile" && !search.article_id ? "" : inferredSelectedArticleId;
  const selectedArticle = findArticleById(articles, selectedArticleId);

  const articleDetailQuery = useArticleDetailQuery(selectedArticleId, !contentIsContextView);
  const fetchFulltextMutation = useFetchArticleFulltextMutation(selectedArticleId);
  const rawReaderContent = useMemo(() => {
    const detail = articleDetailQuery.data;
    if (!detail) {
      return "";
    }

    if (detail.content_source === "full_article") {
      return detail.fulltext_content_html ?? detail.fulltext_content_text ?? detail.content_text ?? "";
    }

    return detail.content_text ?? "";
  }, [articleDetailQuery.data]);
  const readerContentHtml = useMemo(
    () => toReaderHtml(rawReaderContent),
    [rawReaderContent]
  );
  const patchArticleStateMutation = usePatchArticleStateMutation(selectedArticleId);
  const markScopeAsReadMutation = useMarkScopeAsReadMutation();
  const createFolderMutation = useCreateFolderMutation();
  const createFeedMutation = useCreateFeedMutation();
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
    const decision = getReadToggleDecision(selectedArticle);
    if (!decision) {
      return;
    }

    patchArticleStateMutation.mutate(
      decision.payload,
      decision.shouldAdvance
        ? {
            onSuccess: () => {
              moveSelection(1);
            },
          }
        : undefined
    );
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
  const navOpen = usesDrawerNav && isNavOpen;
  const showArticlesPane = layoutMode !== "mobile" || !selectedArticleId;
  const showReaderPane = layoutMode !== "mobile" || Boolean(selectedArticleId);
  const showListReaderSplitter = layoutMode === "desktop" && showArticlesPane && showReaderPane;
  const mobilePaneState: MobilePaneState = navOpen ? "nav" : selectedArticleId ? "reader" : "list";
  const shellClassName = [
    `workspace-shell react-density-${density}`,
    `workspace-shell--${layoutMode}`,
    layoutMode === "mobile" ? `workspace-shell--mobile-pane-${mobilePaneState}` : "",
  ]
    .filter(Boolean)
    .join(" ");
  const desktopShellStyle = layoutMode === "desktop"
    ? ({
        "--workspace-nav-width": `${layout.navWidth}px`,
        "--workspace-list-width": `${layout.listWidth}px`,
      } as CSSProperties)
    : undefined;

  const navigationPane = (
    <NavigationPane
      isReadOnly={layoutMode === "mobile"}
      density={density}
      navPreset={navPreset}
      hierarchy={hierarchy}
      folders={foldersQuery.data ?? []}
      feedIconByFeedId={feedIconByFeedId}
      selectedScopeType={isDashboardView ? "dashboard" : isPluginAreaView ? "plugin" : search.scope_type}
      selectedScopeKey={isDashboardView ? "dashboard" : isPluginAreaView ? activePluginAreaRouteKey ?? "" : selectedScopeKey}
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
      pluginAreas={pluginAreas}
      selectedPluginAreaRouteKey={activePluginAreaRouteKey}
      onSelectPluginArea={(area) => {
        setIsNavOpen(false);
        void navigate({
          to: "/app/plugins/$areaId",
          params: { areaId: area.route_key },
        });
      }}
      onCreateFolder={async (name) => {
        await createFolderMutation.mutateAsync(toCreateFolderRequest(name));
      }}
      onCreateFeed={async ({ title, url, folderId }) => {
        await createFeedMutation.mutateAsync({
          title,
          url,
          folder_id: folderId,
        });
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
      isFeedMutationPending={createFeedMutation.isPending}
      isAssignPending={assignFeedFolderMutation.isPending}
    />
  );

  const feedsAction = {
    id: "feeds",
    label: usesDrawerNav ? "Nav" : "Feeds",
    icon: <RssFeedRoundedIcon fontSize="small" />,
    badge: systemAllCount,
    active: usesDrawerNav
      ? navOpen
      : !contentIsContextView && (search.scope_type !== "system" || search.state === "all"),
    onClick: () => {
      if (usesDrawerNav) {
        setIsNavOpen((previous) => !previous);
        return;
      }
      setSearch({ scope_type: "system", scope_id: "", state: "all", article_id: "" });
    },
  };

  const savedAction = {
    id: "saved",
    label: "Saved",
    icon: <BookmarkBorderRoundedIcon fontSize="small" />,
    badge: systemSavedCount,
    active: !contentIsContextView && search.scope_type === "system" && search.state === "saved",
    onClick: () => setSearch({ scope_type: "system", scope_id: "", state: "saved", article_id: "" }),
  };

  const searchAction = {
    id: "search",
    label: "Search",
    icon: <SearchRoundedIcon fontSize="small" />,
    onClick: () => searchInputRef.current?.focus(),
  };

  const visibleRailActions = isMobile
    ? [
        feedsAction,
        savedAction,
        searchAction,
      ]
    : [
        {
          id: "dashboard",
          label: "Dashboard",
          icon: <SpaceDashboardRoundedIcon fontSize="small" />,
          active: isDashboardView,
          onClick: () => void navigate({ to: "/app/dashboard" }),
        },
        feedsAction,
        savedAction,
        searchAction,
        {
          id: "settings",
          label: "Settings",
          icon: <SettingsRoundedIcon fontSize="small" />,
          onClick: () => void navigate({ to: "/account" }),
        },
        {
          id: "theme",
          label: themeMode === "dark" ? "Light mode" : "Dark mode",
          icon: themeMode === "dark" ? <LightModeRoundedIcon fontSize="small" /> : <DarkModeRoundedIcon fontSize="small" />,
          onClick: () => setThemeMode(themeMode === "dark" ? "light" : "dark"),
        },
        {
          id: "help",
          label: "Help",
          icon: <HelpOutlineRoundedIcon fontSize="small" />,
          onClick: () => void navigate({ to: "/help" }),
        },
      ];

  return (
    <Box className={shellClassName} style={desktopShellStyle} data-layout-mode={layoutMode}>
      <WorkspaceRail actions={visibleRailActions} />

      {usesDrawerNav ? (
        <Drawer open={navOpen} onClose={() => setIsNavOpen(false)} PaperProps={{ className: "workspace-nav-drawer" }}>
          {navigationPane}
        </Drawer>
      ) : (
        <>
          {navigationPane}
          <Box
            {...navSplitterProps}
            className={isNavDragging ? "workspace-splitter workspace-splitter--active" : "workspace-splitter"}
          />
        </>
      )}

      <Box className={layoutMode === "desktop" && !contentIsContextView ? "workspace-content workspace-content--resizable" : "workspace-content"}>
        {isDashboardView ? (
          <DashboardHost
            summary={dashboardSummaryQuery.data}
            isLoading={dashboardSummaryQuery.isLoading}
            isError={dashboardSummaryQuery.isError}
          />
        ) : isPluginAreaView ? (
          <Box className="workspace-plugin-shell">
            {activePluginArea ? (
              <PluginAreaHost area={activePluginArea} />
            ) : (
              <Alert severity="warning">Plugin area not found or currently unavailable.</Alert>
            )}
          </Box>
        ) : (
          <>
            {showArticlesPane ? (
              <ArticlesPane
                density={density}
                search={search}
                scopeLabel={selectedScopeLabel}
                streamNameById={streamNameById}
                articleItems={articles}
                articleTotal={articlesQuery.data?.total ?? 0}
                selectedArticleId={selectedArticleId}
                isLoading={articlesQuery.isLoading}
                isError={articlesQuery.isError}
                searchInputRef={searchInputRef}
                isMarkAllReadPending={markScopeAsReadMutation.isPending}
                onSearchChange={(value) => setSearch({ q: value, article_id: "" })}
                onStateChange={(value) => setSearch({ state: value, article_id: "" })}
                onArticleSelect={(articleId) => setSearch({ article_id: articleId })}
                {...(layoutMode === "mobile"
                  ? {
                      onBackToNav: () => setIsNavOpen(true),
                    }
                  : {})}
                onMarkScopeRead={() => {
                  if (
                    !window.confirm(
                      "Mark all articles in the current scope and filters as read?"
                    )
                  ) {
                    return;
                  }
                  markScopeAsReadMutation.mutate({
                    scope_type: search.scope_type,
                    ...(search.scope_id ? { scope_id: search.scope_id } : {}),
                    state: search.state,
                    ...(search.q ? { q: search.q } : {}),
                  });
                }}
              />
            ) : null}

            {showListReaderSplitter ? (
              <Box
                {...listSplitterProps}
                className={isListDragging ? "workspace-splitter workspace-splitter--active" : "workspace-splitter"}
              />
            ) : null}

            {showReaderPane ? (
              <ReaderPane
                selectedArticle={selectedArticle}
                selectedArticleId={selectedArticleId}
                streamNameById={streamNameById}
                detail={articleDetailQuery.data}
                contentHtml={readerContentHtml}
                isLoading={articleDetailQuery.isLoading}
                isError={articleDetailQuery.isError}
                isMutating={patchArticleStateMutation.isPending}
                hasMutationError={patchArticleStateMutation.isError}
                isFulltextFetching={fetchFulltextMutation.isPending}
                hasFulltextMutationError={fetchFulltextMutation.isError}
                fulltextMutationErrorMessage={fetchFulltextMutation.error?.message ?? null}
                onToggleRead={toggleRead}
                onToggleSaved={toggleSaved}
                onOpenOriginal={() => {
                  const targetUrl = articleDetailQuery.data?.canonical_url ?? selectedArticle?.canonical_url;
                  if (targetUrl) {
                    window.open(targetUrl, "_blank", "noopener,noreferrer");
                  }
                }}
                onFetchFullArticle={() => {
                  fetchFulltextMutation.mutate();
                }}
                onMoveSelection={moveSelection}
                {...(layoutMode === "mobile"
                  ? {
                      onBackToList: () => setSearch({ article_id: "" }),
                      onBackToNav: () => setIsNavOpen(true),
                    }
                  : {})}
              />
            ) : null}
          </>
        )}
      </Box>
    </Box>
  );
}
