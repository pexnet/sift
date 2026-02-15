import { Alert, Box, Typography } from "@mui/material";
import { RouterProvider, createRootRouteWithContext, createRoute, createRouter, redirect, useNavigate } from "@tanstack/react-router";

import { DEFAULT_WORKSPACE_SEARCH, parseWorkspaceSearch } from "../entities/article/model";
import { getCurrentUser } from "../shared/api/authApi";
import type { WorkspaceSearch } from "../shared/types/contracts";
import { AccountPage } from "../features/auth/routes/AccountPage";
import { LoginPage } from "../features/auth/routes/LoginPage";
import { RegisterPage } from "../features/auth/routes/RegisterPage";
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
    throw redirect({ to: "/app", search: DEFAULT_WORKSPACE_SEARCH });
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
      <button type="button" onClick={() => void navigate({ to: "/app", search: DEFAULT_WORKSPACE_SEARCH })}>
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
      throw redirect({ to: "/app", search: DEFAULT_WORKSPACE_SEARCH });
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

const accountRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/account",
  beforeLoad: ({ context }) => requireAuth(context),
  component: AccountPage,
});

function WorkspaceRouteComponent() {
  const navigate = useNavigate({ from: "/app" });
  const { density, setDensity, themeMode, setThemeMode } = useAppUiState();
  const search = workspaceRoute.useSearch();

  const setSearch = (patch: Partial<WorkspaceSearch>) => {
    void navigate({
      to: "/app",
      search: (previous: WorkspaceSearch) => ({ ...previous, ...patch }),
    });
  };

  return (
    <WorkspacePage
      search={search}
      density={density}
      themeMode={themeMode}
      setDensity={setDensity}
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

const routeTree = rootRoute.addChildren([indexRoute, loginRoute, registerRoute, accountRoute, workspaceRoute]);

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
