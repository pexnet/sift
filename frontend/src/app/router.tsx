import { Alert, Box, Typography } from "@mui/material";
import { RouterProvider, createRootRouteWithContext, createRoute, createRouter, redirect, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import {
  loadPersistedWorkspaceSearch,
  parseWorkspaceSearch,
  savePersistedWorkspaceSearch,
} from "../entities/article/model";
import { getCurrentUser } from "../shared/api/authApi";
import type { WorkspaceSearch } from "../shared/types/contracts";
import { AccountPage } from "../features/auth/routes/AccountPage";
import { FeedHealthPage } from "../features/feed-health/routes/FeedHealthPage";
import { HelpPage } from "../features/help/routes/HelpPage";
import { LoginPage } from "../features/auth/routes/LoginPage";
import { RegisterPage } from "../features/auth/routes/RegisterPage";
import { MonitoringFeedsPage } from "../features/monitoring/routes/MonitoringFeedsPage";
import { SettingsWorkspaceShell } from "../features/settings/components/SettingsWorkspaceShell";
import { WorkspacePage } from "../features/workspace/routes/WorkspacePage";
import { AppProviders, queryClient, useAppUiState } from "./providers";
import { AppShell } from "./AppShell";

type RouterContext = {
  queryClient: typeof queryClient;
};

async function fetchCurrentUser(context: RouterContext) {
  return context.queryClient.fetchQuery({
    queryKey: ["auth", "me"],
    queryFn: getCurrentUser,
    staleTime: 30_000,
  });
}

async function requireAuth(context: RouterContext) {
  const user = await fetchCurrentUser(context);
  if (!user) {
    throw redirect({ to: "/login" });
  }
}

async function requireAnonymous(context: RouterContext) {
  const user = await fetchCurrentUser(context);
  if (user) {
    throw redirect({ to: "/app", search: loadPersistedWorkspaceSearch() });
  }
}

function guardMobileReadOnlyRoute() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return;
  }
  if (window.matchMedia("(max-width: 760px)").matches) {
    throw redirect({ to: "/app", search: loadPersistedWorkspaceSearch() });
  }
}

function RootErrorBoundary() {
  return (
    <Alert severity="error" sx={{ m: 3 }}>
      Unexpected application error.
    </Alert>
  );
}

function NotFoundBoundary() {
  const navigate = useNavigate();

  return (
    <Box className="panel auth-panel" sx={{ mt: 3 }}>
      <Typography variant="h5" component="h1" sx={{ mb: 1 }}>
        Page not found
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        The requested page does not exist.
      </Typography>
      <button type="button" onClick={() => void navigate({ to: "/app", search: loadPersistedWorkspaceSearch() })}>
        Go to workspace
      </button>
    </Box>
  );
}

const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: AppShell,
  errorComponent: RootErrorBoundary,
  notFoundComponent: NotFoundBoundary,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: async ({ context }) => {
    const user = await fetchCurrentUser(context);
    if (user) {
      throw redirect({ to: "/app", search: loadPersistedWorkspaceSearch() });
    }
    throw redirect({ to: "/login" });
  },
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  beforeLoad: ({ context }) => requireAnonymous(context),
  component: LoginPage,
});

const registerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/register",
  beforeLoad: ({ context }) => requireAnonymous(context),
  component: RegisterPage,
});

function AccountRouteComponent() {
  return (
    <SettingsWorkspaceShell>
      <AccountPage />
    </SettingsWorkspaceShell>
  );
}

const accountRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/account",
  beforeLoad: async ({ context }) => {
    await requireAuth(context);
    guardMobileReadOnlyRoute();
  },
  component: AccountRouteComponent,
});

function MonitoringRouteComponent() {
  return (
    <SettingsWorkspaceShell>
      <MonitoringFeedsPage />
    </SettingsWorkspaceShell>
  );
}

const monitoringFeedsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/account/monitoring",
  beforeLoad: async ({ context }) => {
    await requireAuth(context);
    guardMobileReadOnlyRoute();
  },
  component: MonitoringRouteComponent,
});

function FeedHealthRouteComponent() {
  return (
    <SettingsWorkspaceShell>
      <FeedHealthPage />
    </SettingsWorkspaceShell>
  );
}

const feedHealthRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/account/feed-health",
  beforeLoad: async ({ context }) => {
    await requireAuth(context);
    guardMobileReadOnlyRoute();
  },
  component: FeedHealthRouteComponent,
});

function HelpRouteComponent() {
  return (
    <SettingsWorkspaceShell>
      <HelpPage />
    </SettingsWorkspaceShell>
  );
}

const helpRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/help",
  beforeLoad: async ({ context }) => {
    await requireAuth(context);
    guardMobileReadOnlyRoute();
  },
  component: HelpRouteComponent,
});

function WorkspaceRouteComponent() {
  const navigate = useNavigate({ from: "/app" });
  const { density, navPreset, themeMode, setThemeMode } = useAppUiState();
  const search = workspaceRoute.useSearch();

  useEffect(() => {
    savePersistedWorkspaceSearch(search);
  }, [search]);

  const setSearch = (patch: Partial<WorkspaceSearch>) => {
    const nextSearch: WorkspaceSearch = { ...search, ...patch };
    savePersistedWorkspaceSearch(nextSearch);
    void navigate({
      to: "/app",
      search: nextSearch,
    });
  };

  return (
    <WorkspacePage
      search={search}
      density={density}
      navPreset={navPreset}
      themeMode={themeMode}
      setThemeMode={setThemeMode}
      setSearch={setSearch}
    />
  );
}

const workspaceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app",
  validateSearch: (search) => parseWorkspaceSearch(search),
  beforeLoad: ({ context }) => requireAuth(context),
  component: WorkspaceRouteComponent,
});

function PluginWorkspaceRouteComponent() {
  const navigate = useNavigate();
  const { density, navPreset, themeMode, setThemeMode } = useAppUiState();
  const { areaId } = pluginWorkspaceRoute.useParams();
  const [searchState, setSearchState] = useState(loadPersistedWorkspaceSearch());

  const setSearch = (patch: Partial<WorkspaceSearch>) => {
    setSearchState((previous) => {
      const nextSearch: WorkspaceSearch = { ...previous, ...patch };
      savePersistedWorkspaceSearch(nextSearch);
      void navigate({
        to: "/app",
        search: nextSearch,
      });
      return nextSearch;
    });
  };

  return (
    <WorkspacePage
      search={searchState}
      density={density}
      navPreset={navPreset}
      themeMode={themeMode}
      setThemeMode={setThemeMode}
      setSearch={setSearch}
      activePluginAreaRouteKey={areaId}
    />
  );
}

const pluginWorkspaceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/app/plugins/$areaId",
  beforeLoad: ({ context }) => requireAuth(context),
  component: PluginWorkspaceRouteComponent,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  registerRoute,
  accountRoute,
  feedHealthRoute,
  monitoringFeedsRoute,
  helpRoute,
  pluginWorkspaceRoute,
  workspaceRoute,
]);

const router = createRouter({
  routeTree,
  context: {
    queryClient,
  },
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function AppRouterProvider() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
