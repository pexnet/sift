import { Box, Button, Stack } from "@mui/material";
import { Link, Outlet, useLocation, useNavigate } from "@tanstack/react-router";

import { useCurrentUser, useLogoutMutation } from "../features/auth/api/authHooks";
import { DEFAULT_WORKSPACE_SEARCH } from "../entities/article/model";
import { useAppUiState } from "./providers";
import { joinClassNames } from "../shared/lib/joinClassNames";

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { themeMode, setThemeMode, density } = useAppUiState();

  const currentUserQuery = useCurrentUser();
  const logoutMutation = useLogoutMutation();

  const isWorkspaceRoute = location.pathname === "/app";

  return (
    <main className={joinClassNames("layout", isWorkspaceRoute && "workspace-layout")}>
      <Box component="nav" className="topnav">
        <Link to="/app" search={DEFAULT_WORKSPACE_SEARCH} className="brand">
          Sift
        </Link>
        <Box className="actions">
          <Button
            type="button"
            id="theme-toggle"
            className="icon-btn"
            size="small"
            variant="text"
            onClick={() => setThemeMode(themeMode === "dark" ? "light" : "dark")}
          >
            {themeMode === "dark" ? "Light" : "Dark"}
          </Button>

          {currentUserQuery.data ? (
            <Stack direction="row" spacing={1} alignItems="center">
              <Link to="/account">
                {currentUserQuery.data.display_name || currentUserQuery.data.email}
              </Link>
              <Button
                type="button"
                size="small"
                variant="text"
                onClick={() => {
                  logoutMutation.mutate(undefined, {
                    onSuccess: () => {
                      void navigate({ to: "/login" });
                    },
                  });
                }}
              >
                Logout
              </Button>
            </Stack>
          ) : (
            <Stack direction="row" spacing={1} alignItems="center">
              <Link to="/login">
                Login
              </Link>
              <Link to="/register">
                Register
              </Link>
            </Stack>
          )}
        </Box>
      </Box>

      <Stack className={joinClassNames(isWorkspaceRoute ? "react-workspace" : "react-auth-shell", `react-density-${density}`)} spacing={isWorkspaceRoute ? 2 : 0}>
        <Outlet />
      </Stack>
    </main>
  );
}
