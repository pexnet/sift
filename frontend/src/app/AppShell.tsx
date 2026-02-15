import { Box, Button, Stack, Typography } from "@mui/material";
import { Link, Outlet, useLocation, useNavigate } from "@tanstack/react-router";

import { DEFAULT_WORKSPACE_SEARCH } from "../entities/article/model";
import { useCurrentUser, useLogoutMutation } from "../features/auth/api/authHooks";
import { joinClassNames } from "../shared/lib/joinClassNames";

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentUserQuery = useCurrentUser();
  const logoutMutation = useLogoutMutation();

  const isWorkspaceRoute = location.pathname === "/app";

  if (isWorkspaceRoute) {
    return (
      <main className={joinClassNames("layout", "workspace-layout")}>
        <Outlet />
      </main>
    );
  }

  return (
    <main className="layout">
      <Box component="nav" className="topnav">
        <Link to="/app" search={DEFAULT_WORKSPACE_SEARCH} className="brand">
          Sift
        </Link>
        {currentUserQuery.data ? (
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2">{currentUserQuery.data.display_name || currentUserQuery.data.email}</Typography>
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
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </Stack>
        )}
      </Box>

      <Stack className="react-auth-shell" spacing={0}>
        <Outlet />
      </Stack>
    </main>
  );
}
