import React, { useEffect, useMemo, useRef, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "https://esm.sh/@tanstack/react-query@5.66.4";
import {
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
  useNavigate,
} from "https://esm.sh/@tanstack/react-router@1.114.26";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  CssBaseline,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  LinearProgress,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  ThemeProvider,
  Typography,
  createTheme,
} from "https://esm.sh/@mui/material@5.16.14?deps=react@18.3.1,react-dom@18.3.1";

const THEME_KEY = "sift-theme";
const DENSITY_KEY = "sift-density";

const rootElement = document.getElementById("react-workspace-root");
const appElement = document.getElementById("react-workspace-app");

if (!(rootElement instanceof HTMLElement) || !(appElement instanceof HTMLElement)) {
  throw new Error("React workspace root is missing");
}

const apiConfig = {
  navigationEndpoint: rootElement.dataset.navigationEndpoint || "/api/v1/navigation",
  articlesEndpoint: rootElement.dataset.articlesEndpoint || "/api/v1/articles",
  articleEndpointTemplate: rootElement.dataset.articleEndpointTemplate || "/api/v1/articles/{article_id}",
  articleStateEndpointTemplate: rootElement.dataset.articleStateEndpointTemplate || "/api/v1/articles/{article_id}/state",
};

const queryClient = new QueryClient();

function getStoredTheme() {
  return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
}

function getStoredDensity() {
  return localStorage.getItem(DENSITY_KEY) === "comfortable" ? "comfortable" : "compact";
}

function fetchJson(url, options) {
  return fetch(url, { credentials: "same-origin", ...options }).then((response) => {
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  });
}

function flattenNavigation(navigation) {
  return [
    ...(navigation.system || []).map((item) => ({ ...item, scope_type: "system" })),
    ...(navigation.folders || []).map((item) => ({ ...item, scope_type: "folder" })),
    ...(navigation.streams || []).map((item) => ({ ...item, scope_type: "stream" })),
  ];
}

function buildDashboardCards({ navigation, articles, scopeLabel }) {
  const systemNodes = navigation?.system || [];
  const allNode = systemNodes.find((item) => item.key === "all");
  const savedNode = systemNodes.find((item) => item.key === "saved");
  const freshNode = systemNodes.find((item) => item.key === "fresh");
  const totalArticles = articles.length;
  const unreadInList = articles.filter((item) => !item.is_read).length;
  const savedInList = articles.filter((item) => item.is_starred).length;
  const activeSources = new Set(articles.map((item) => item.feed_title || item.feed_id).filter(Boolean)).size;
  const freshRatio = totalArticles === 0 ? 0 : Math.round((unreadInList / totalArticles) * 100);

  return [
    {
      id: "scope",
      title: "Current scope",
      value: scopeLabel,
      hint: `${totalArticles} loaded in this view`,
      size: "md",
    },
    {
      id: "unread",
      title: "Unread",
      value: String(unreadInList),
      hint: `${allNode?.unread_count || 0} total unread across account`,
      size: "sm",
    },
    {
      id: "saved",
      title: "Saved",
      value: String(savedInList),
      hint: `${savedNode?.unread_count || 0} saved entries in navigation`,
      size: "sm",
    },
    {
      id: "fresh",
      title: "Fresh coverage",
      value: `${freshRatio}%`,
      hint: `${freshNode?.unread_count || 0} fresh entries in navigation`,
      progress: freshRatio,
      size: "lg",
    },
    {
      id: "sources",
      title: "Active sources",
      value: String(activeSources),
      hint: "Distinct feeds represented in loaded articles",
      size: "md",
    },
  ];
}

function DashboardCard({ card }) {
  return React.createElement(
    Card,
    { variant: "outlined", sx: { height: "100%", borderRadius: 3 } },
    React.createElement(
      CardContent,
      null,
      React.createElement(Typography, { variant: "overline", color: "text.secondary" }, card.title),
      React.createElement(Typography, { variant: "h5", sx: { mb: 0.5 } }, card.value),
      card.progress !== undefined ? React.createElement(LinearProgress, { value: card.progress, variant: "determinate", sx: { mb: 1 } }) : null,
      React.createElement(Typography, { variant: "body2", color: "text.secondary" }, card.hint)
    )
  );
}

function WorkspacePage({ themeMode, setThemeMode, density, setDensity }) {
  const queryClientRef = useQueryClient();
  const navigate = useNavigate({ from: "/" });
  const search = Route.useSearch();
  const searchInputRef = useRef(null);

  const navigationQuery = useQuery({
    queryKey: ["navigation"],
    queryFn: () => fetchJson(apiConfig.navigationEndpoint),
  });

  const articlesQuery = useQuery({
    queryKey: ["articles", search.scope_type, search.scope_id, search.state, search.sort, search.q],
    queryFn: () => {
      const query = new URLSearchParams({
        scope_type: search.scope_type,
        state: search.state,
        sort: search.sort,
        limit: "50",
        offset: "0",
      });
      if (search.scope_id) {
        query.set("scope_id", search.scope_id);
      }
      if (search.q) {
        query.set("q", search.q);
      }
      return fetchJson(`${apiConfig.articlesEndpoint}?${query.toString()}`);
    },
  });

  const articleItems = articlesQuery.data?.items || [];
  const selectedArticleId = search.article_id || articleItems[0]?.id || "";

  const articleDetailQuery = useQuery({
    queryKey: ["article", selectedArticleId],
    queryFn: () => fetchJson(apiConfig.articleEndpointTemplate.replace("{article_id}", selectedArticleId)),
    enabled: Boolean(selectedArticleId),
  });

  const updateArticleMutation = useMutation({
    mutationFn: ({ articleId, payload }) =>
      fetchJson(apiConfig.articleStateEndpointTemplate.replace("{article_id}", articleId), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClientRef.invalidateQueries({ queryKey: ["articles"] }),
        queryClientRef.invalidateQueries({ queryKey: ["article", selectedArticleId] }),
      ]);
    },
  });

  const navItems = navigationQuery.data ? flattenNavigation(navigationQuery.data) : [];
  const selectedArticle = articleItems.find((article) => article.id === selectedArticleId);
  const selectedScopeKey = search.scope_id || (search.scope_type === "system" ? "all" : "");
  const selectedNavLabel =
    navItems.find((item) => search.scope_type === item.scope_type && selectedScopeKey === (item.id || item.key || ""))?.title ||
    navItems.find((item) => search.scope_type === item.scope_type && selectedScopeKey === (item.id || item.key || ""))?.name ||
    "All articles";
  const dashboardCards = buildDashboardCards({
    navigation: navigationQuery.data,
    articles: articleItems,
    scopeLabel: selectedNavLabel,
  });

  const setSearch = (patch) => {
    navigate({ to: "/", search: { ...search, ...patch } });
  };

  const moveSelection = (delta) => {
    if (articleItems.length === 0) {
      return;
    }
    const currentIndex = Math.max(
      0,
      articleItems.findIndex((article) => article.id === selectedArticleId)
    );
    const nextIndex = Math.max(0, Math.min(articleItems.length - 1, currentIndex + delta));
    setSearch({ article_id: articleItems[nextIndex].id });
  };

  const toggleSelectedArticleState = (field) => {
    if (!selectedArticle) {
      return;
    }
    const currentValue = Boolean(selectedArticle[field]);
    updateArticleMutation.mutate({
      articleId: selectedArticle.id,
      payload: { [field]: !currentValue },
    });
  };

  useEffect(() => {
    const onKeyDown = (event) => {
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
      } else if (event.key === "k") {
        event.preventDefault();
        moveSelection(-1);
      } else if (event.key === "o") {
        event.preventDefault();
        if (!search.article_id && articleItems.length > 0) {
          setSearch({ article_id: articleItems[0].id });
        }
      } else if (event.key === "m") {
        event.preventDefault();
        toggleSelectedArticleState("is_read");
      } else if (event.key === "s") {
        event.preventDefault();
        toggleSelectedArticleState("is_starred");
      } else if (event.key === "/") {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [articleItems, search.article_id, selectedArticle, updateArticleMutation]);

  return React.createElement(
    Stack,
    { spacing: 2 },
    React.createElement(
      Box,
      { component: "section" },
      React.createElement(Typography, { variant: "h6", sx: { mb: 1 } }, "Dashboard"),
      React.createElement(
        Grid,
        { container: true, spacing: 1.5, sx: { mb: 0.5 } },
        dashboardCards.map((card) =>
          React.createElement(
            Grid,
            {
              key: card.id,
              item: true,
              xs: 12,
              sm: card.size === "sm" ? 6 : 12,
              md: card.size === "lg" ? 6 : 3,
            },
            React.createElement(DashboardCard, { card })
          )
        )
      )
    ),
    React.createElement(
      Stack,
      { className: `react-workspace__grid react-density-${density}`, spacing: 2 },
    React.createElement(
      Paper,
      { className: "react-pane", component: "section", elevation: 0 },
      React.createElement(
        Stack,
        { direction: "row", justifyContent: "space-between", alignItems: "center", sx: { mb: 1 } },
        React.createElement(Typography, { variant: "h6" }, "Navigation"),
        React.createElement(
          Stack,
          { direction: "row", spacing: 1 },
          React.createElement(
            Button,
            {
              size: "small",
              variant: "outlined",
              onClick: () => setThemeMode(themeMode === "dark" ? "light" : "dark"),
            },
            themeMode === "dark" ? "Light" : "Dark"
          ),
          React.createElement(
            FormControl,
            { size: "small", sx: { minWidth: 130 } },
            React.createElement(InputLabel, { id: "density-select-label" }, "Density"),
            React.createElement(
              Select,
              {
                labelId: "density-select-label",
                value: density,
                label: "Density",
                onChange: (event) => setDensity(event.target.value),
              },
              React.createElement(MenuItem, { value: "compact" }, "Compact"),
              React.createElement(MenuItem, { value: "comfortable" }, "Comfortable")
            )
          )
        )
      ),
      navigationQuery.isLoading ? React.createElement(CircularProgress, { size: 20 }) : null,
      navigationQuery.isError ? React.createElement(Alert, { severity: "error" }, "Failed to load navigation.") : null,
      !navigationQuery.isLoading && !navigationQuery.isError && navItems.length === 0
        ? React.createElement(Typography, { variant: "body2", color: "text.secondary" }, "No navigation items.")
        : null,
      React.createElement(
        List,
        { dense: density === "compact" },
        navItems.map((item) =>
          React.createElement(
            ListItem,
            { disablePadding: true, key: `${item.scope_type}:${item.id || item.key}` },
            React.createElement(
              ListItemButton,
              {
                selected:
                  search.scope_type === item.scope_type &&
                  selectedScopeKey === (item.id || item.key || ""),
                onClick: () =>
                  setSearch({
                    scope_type: item.scope_type,
                    scope_id: item.id || item.key || "",
                    article_id: "",
                  }),
              },
              React.createElement(ListItemText, {
                primary: item.title || item.name || item.key || "Untitled",
                secondary: item.scope_type,
              })
            )
          )
        )
      )
    ),
    React.createElement(
      Paper,
      { className: "react-pane", component: "section", elevation: 0 },
      React.createElement(Typography, { variant: "h6", gutterBottom: true }, "Articles"),
      React.createElement(
        Stack,
        { direction: { xs: "column", sm: "row" }, spacing: 1, sx: { mb: 1, flexWrap: "wrap" } },
        React.createElement(TextField, {
          size: "small",
          label: "Search",
          inputRef: searchInputRef,
          value: search.q,
          onChange: (event) => setSearch({ q: event.target.value, article_id: "" }),
        }),
        React.createElement(
          TextField,
          {
            size: "small",
            select: true,
            label: "State",
            value: search.state,
            onChange: (event) => setSearch({ state: event.target.value, article_id: "" }),
            sx: { minWidth: 140 },
          },
          React.createElement(MenuItem, { value: "all" }, "All"),
          React.createElement(MenuItem, { value: "unread" }, "Unread"),
          React.createElement(MenuItem, { value: "saved" }, "Saved"),
          React.createElement(MenuItem, { value: "archived" }, "Archived"),
          React.createElement(MenuItem, { value: "fresh" }, "Fresh"),
          React.createElement(MenuItem, { value: "recent" }, "Recent")
        )
      ),
      articlesQuery.isLoading ? React.createElement(CircularProgress, { size: 20 }) : null,
      articlesQuery.isError ? React.createElement(Alert, { severity: "error" }, "Failed to load articles.") : null,
      !articlesQuery.isLoading && !articlesQuery.isError && articleItems.length === 0
        ? React.createElement(Typography, { variant: "body2", color: "text.secondary" }, "No articles found.")
        : null,
      React.createElement(
        List,
        { dense: density === "compact" },
        articleItems.map((article) =>
          React.createElement(
            ListItem,
            { disablePadding: true, key: article.id },
            React.createElement(
              ListItemButton,
              {
                selected: selectedArticleId === article.id,
                onClick: () => setSearch({ article_id: article.id }),
              },
              React.createElement(ListItemText, {
                primary: article.title || "Untitled article",
                secondary: article.feed_title || article.author || "",
              })
            )
          )
        )
      )
    ),
    React.createElement(
      Paper,
      { className: "react-pane", component: "section", elevation: 0 },
      React.createElement(Typography, { variant: "h6", gutterBottom: true }, "Reader"),
      selectedArticle
        ? React.createElement(
            Stack,
            { direction: "row", spacing: 1, sx: { mb: 2, flexWrap: "wrap" } },
            React.createElement(
              Button,
              {
                size: "small",
                variant: "outlined",
                onClick: () => toggleSelectedArticleState("is_read"),
                disabled: updateArticleMutation.isPending,
              },
              selectedArticle.is_read ? "Mark unread" : "Mark read"
            ),
            React.createElement(
              Button,
              {
                size: "small",
                variant: "outlined",
                onClick: () => toggleSelectedArticleState("is_starred"),
                disabled: updateArticleMutation.isPending,
              },
              selectedArticle.is_starred ? "Unsave" : "Save"
            ),
            selectedArticle.is_archived ? React.createElement(Chip, { size: "small", label: "Archived" }) : null
          )
        : null,
      updateArticleMutation.isError
        ? React.createElement(Alert, { severity: "error", sx: { mb: 1 } }, "Failed to update article state.")
        : null,
      !selectedArticleId
        ? React.createElement(
            Typography,
            { variant: "body2", color: "text.secondary" },
            "Select an article to load reader content."
          )
        : null,
      articleDetailQuery.isLoading ? React.createElement(CircularProgress, { size: 20 }) : null,
      articleDetailQuery.isError
        ? React.createElement(Alert, { severity: "error" }, "Failed to load article details.")
        : null,
      selectedArticleId && articleDetailQuery.data
        ? React.createElement(
            Box,
            null,
            React.createElement(Typography, { variant: "h6" }, articleDetailQuery.data.title || "Untitled article"),
            React.createElement(
              Typography,
              { variant: "body2", color: "text.secondary", gutterBottom: true },
              articleDetailQuery.data.author || articleDetailQuery.data.feed_title || ""
            ),
            React.createElement(Divider, { sx: { mb: 2 } }),
            React.createElement(
              Typography,
              { variant: "body2" },
              articleDetailQuery.data.content_text || "No content available."
            )
          )
        : null
    )
    )
  );
}

const rootRoute = createRootRoute({
  component: () => React.createElement(WorkspaceApp),
});

const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: (search) => ({
    scope_type: typeof search.scope_type === "string" ? search.scope_type : "system",
    scope_id: typeof search.scope_id === "string" ? search.scope_id : "",
    state: typeof search.state === "string" ? search.state : "all",
    sort: typeof search.sort === "string" ? search.sort : "newest",
    q: typeof search.q === "string" ? search.q : "",
    article_id: typeof search.article_id === "string" ? search.article_id : "",
  }),
});

function WorkspaceApp() {
  const [themeMode, setThemeMode] = useState(getStoredTheme);
  const [density, setDensity] = useState(getStoredDensity);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", themeMode);
    localStorage.setItem(THEME_KEY, themeMode);
  }, [themeMode]);

  useEffect(() => {
    localStorage.setItem(DENSITY_KEY, density);
  }, [density]);

  const theme = useMemo(() => createTheme({ palette: { mode: themeMode } }), [themeMode]);

  return React.createElement(
    ThemeProvider,
    { theme },
    React.createElement(CssBaseline, null),
    React.createElement(
      WorkspacePage,
      {
        themeMode,
        setThemeMode,
        density,
        setDensity,
      },
      null
    )
  );
}

const routeTree = rootRoute.addChildren([Route]);
const router = createRouter({ routeTree });

createRoot(appElement).render(
  React.createElement(
    React.StrictMode,
    null,
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      React.createElement(RouterProvider, { router })
    )
  )
);
