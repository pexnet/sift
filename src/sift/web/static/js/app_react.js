import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
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
  CircularProgress,
  CssBaseline,
  Divider,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  ThemeProvider,
  Typography,
  createTheme,
} from "https://esm.sh/@mui/material@5.16.14?deps=react@18.3.1,react-dom@18.3.1";

const rootElement = document.getElementById("react-workspace-root");
const appElement = document.getElementById("react-workspace-app");

if (!(rootElement instanceof HTMLElement) || !(appElement instanceof HTMLElement)) {
  throw new Error("React workspace root is missing");
}

const apiConfig = {
  navigationEndpoint: rootElement.dataset.navigationEndpoint || "/api/v1/navigation",
  articlesEndpoint: rootElement.dataset.articlesEndpoint || "/api/v1/articles",
  articleEndpointTemplate: rootElement.dataset.articleEndpointTemplate || "/api/v1/articles/{article_id}",
};

const queryClient = new QueryClient();
const theme = createTheme({
  palette: { mode: document.documentElement.dataset.theme === "dark" ? "dark" : "light" },
});

async function fetchJson(url) {
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function flattenNavigation(navigation) {
  return [
    ...(navigation.system || []).map((item) => ({ ...item, scope_type: "system" })),
    ...(navigation.folders || []).map((item) => ({ ...item, scope_type: "folder" })),
    ...(navigation.streams || []).map((item) => ({ ...item, scope_type: "stream" })),
  ];
}

function WorkspacePage() {
  const navigate = useNavigate({ from: "/" });
  const search = Route.useSearch();

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

  const selectedArticleId = search.article_id || articlesQuery.data?.items?.[0]?.id || "";

  const articleDetailQuery = useQuery({
    queryKey: ["article", selectedArticleId],
    queryFn: () => fetchJson(apiConfig.articleEndpointTemplate.replace("{article_id}", selectedArticleId)),
    enabled: Boolean(selectedArticleId),
  });

  const navItems = navigationQuery.data ? flattenNavigation(navigationQuery.data) : [];

  return React.createElement(
    Stack,
    { className: "react-workspace__grid", spacing: 2 },
    React.createElement(
      Paper,
      { className: "react-pane", component: "section", elevation: 0 },
      React.createElement(Typography, { variant: "h6", gutterBottom: true }, "Navigation"),
      navigationQuery.isLoading
        ? React.createElement(CircularProgress, { size: 20 })
        : null,
      navigationQuery.isError
        ? React.createElement(Alert, { severity: "error" }, "Failed to load navigation.")
        : null,
      !navigationQuery.isLoading && !navigationQuery.isError && navItems.length === 0
        ? React.createElement(Typography, { variant: "body2", color: "text.secondary" }, "No navigation items.")
        : null,
      React.createElement(
        List,
        { dense: true },
        navItems.map((item) =>
          React.createElement(
            ListItem,
            { disablePadding: true, key: `${item.scope_type}:${item.id || item.key}` },
            React.createElement(
              ListItemButton,
              {
                selected: search.scope_type === item.scope_type && search.scope_id === (item.id || ""),
                onClick: () =>
                  navigate({
                    to: "/",
                    search: {
                      ...search,
                      scope_type: item.scope_type,
                      scope_id: item.id || "",
                      article_id: "",
                    },
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
      articlesQuery.isLoading ? React.createElement(CircularProgress, { size: 20 }) : null,
      articlesQuery.isError ? React.createElement(Alert, { severity: "error" }, "Failed to load articles.") : null,
      !articlesQuery.isLoading && !articlesQuery.isError && (articlesQuery.data?.items || []).length === 0
        ? React.createElement(Typography, { variant: "body2", color: "text.secondary" }, "No articles found.")
        : null,
      React.createElement(
        List,
        { dense: true },
        (articlesQuery.data?.items || []).map((article) =>
          React.createElement(
            ListItem,
            { disablePadding: true, key: article.id },
            React.createElement(
              ListItemButton,
              {
                selected: selectedArticleId === article.id,
                onClick: () =>
                  navigate({
                    to: "/",
                    search: { ...search, article_id: article.id },
                  }),
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
      articleDetailQuery.data
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
  );
}

const rootRoute = createRootRoute({
  component: () => React.createElement(WorkspacePage),
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

const routeTree = rootRoute.addChildren([Route]);
const router = createRouter({ routeTree });

createRoot(appElement).render(
  React.createElement(
    React.StrictMode,
    null,
    React.createElement(
      ThemeProvider,
      { theme },
      React.createElement(CssBaseline, null),
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(RouterProvider, { router })
      )
    )
  )
);
