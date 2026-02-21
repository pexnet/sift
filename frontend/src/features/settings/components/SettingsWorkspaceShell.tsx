import BookmarkBorderRoundedIcon from "@mui/icons-material/BookmarkBorderRounded";
import DarkModeRoundedIcon from "@mui/icons-material/DarkModeRounded";
import HelpOutlineRoundedIcon from "@mui/icons-material/HelpOutlineRounded";
import LightModeRoundedIcon from "@mui/icons-material/LightModeRounded";
import RssFeedRoundedIcon from "@mui/icons-material/RssFeedRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import { useLocation, useNavigate } from "@tanstack/react-router";
import { Box, Drawer, IconButton, Tooltip, useMediaQuery } from "@mui/material";
import { useMemo, useState, type CSSProperties, type ReactNode } from "react";

import { loadPersistedWorkspaceSearch } from "../../../entities/article/model";
import type { WorkspaceSearch } from "../../../shared/types/contracts";
import { useAppUiState } from "../../../app/providers";
import { toNavigationHierarchy } from "../../../entities/navigation/model";
import { useNavigationQuery } from "../../workspace/api/workspaceHooks";
import { WorkspaceRail } from "../../workspace/components/WorkspaceRail";
import { usePaneResizing } from "../../workspace/hooks/usePaneResizing";
import { SettingsSubMenuPane } from "./SettingsSubMenuPane";

type SettingsWorkspaceShellProps = {
  children: ReactNode;
};

type SettingsSectionId = "general" | "feed-health" | "monitoring" | "help";

function getActiveSection(pathname: string): SettingsSectionId {
  if (pathname === "/account/feed-health") {
    return "feed-health";
  }
  if (pathname === "/account/monitoring") {
    return "monitoring";
  }
  if (pathname === "/help") {
    return "help";
  }
  return "general";
}

export function SettingsWorkspaceShell({ children }: SettingsWorkspaceShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { density, navPreset, themeMode, setThemeMode } = useAppUiState();
  const [isNavOpen, setIsNavOpen] = useState(false);
  const isTabletOrMobile = useMediaQuery("(max-width: 980px)");
  const {
    layout,
    navSplitterProps,
    isNavDragging,
  } = usePaneResizing({ enabled: !isTabletOrMobile });

  const navigationQuery = useNavigationQuery();
  const hierarchy = useMemo(
    () => (navigationQuery.data ? toNavigationHierarchy(navigationQuery.data) : null),
    [navigationQuery.data]
  );

  const openWorkspace = (search: Partial<WorkspaceSearch>) => {
    const persistedSearch = loadPersistedWorkspaceSearch();
    void navigate({
      to: "/app",
      search: {
        ...persistedSearch,
        ...search,
        article_id: "",
      },
    });
  };

  const systemAllCount = hierarchy?.systems.find((system) => system.scope_id === "all")?.unread_count ?? 0;
  const systemSavedCount = hierarchy?.systems.find((system) => system.scope_id === "saved")?.unread_count ?? 0;
  const isSettingsRoute = location.pathname.startsWith("/account");
  const isHelpRoute = location.pathname === "/help";
  const activeSection = getActiveSection(location.pathname);
  const navOpen = isTabletOrMobile && isNavOpen;
  const desktopShellStyle = !isTabletOrMobile
    ? ({
      "--workspace-nav-width": `${layout.navWidth}px`,
    } as CSSProperties)
    : undefined;

  const navigationPane = (
    <SettingsSubMenuPane
      density={density}
      navPreset={navPreset}
      activeSection={activeSection}
      onSelect={(path) => {
        void navigate({ to: path });
        setIsNavOpen(false);
      }}
    />
  );

  return (
    <Box className={`workspace-shell react-density-${density}`} style={desktopShellStyle}>
      <WorkspaceRail
        actions={[
          {
            id: "settings-nav",
            label: isTabletOrMobile ? "Menu" : "Settings",
            icon: <SettingsRoundedIcon fontSize="small" />,
            active: navOpen,
            onClick: () => {
              if (isTabletOrMobile) {
                setIsNavOpen((previous) => !previous);
                return;
              }
              void navigate({ to: "/account" });
            },
          },
          {
            id: "feeds",
            label: "Feeds",
            icon: <RssFeedRoundedIcon fontSize="small" />,
            badge: systemAllCount,
            onClick: () => openWorkspace({ scope_type: "system", scope_id: "" }),
          },
          {
            id: "saved",
            label: "Saved",
            icon: <BookmarkBorderRoundedIcon fontSize="small" />,
            badge: systemSavedCount,
            onClick: () => openWorkspace({ scope_type: "system", scope_id: "", state: "saved" }),
          },
          {
            id: "settings",
            label: "Settings",
            icon: <SettingsRoundedIcon fontSize="small" />,
            active: isSettingsRoute && !navOpen,
            onClick: () => void navigate({ to: "/account" }),
          },
          {
            id: "help",
            label: "Help",
            icon: <HelpOutlineRoundedIcon fontSize="small" />,
            active: isHelpRoute,
            onClick: () => void navigate({ to: "/help" }),
          },
        ]}
      />

      {isTabletOrMobile ? (
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

      <Box className="workspace-content">
        <Box className="workspace-topbar">
          <Tooltip title={themeMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
            <IconButton
              size="small"
              aria-label={themeMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              onClick={() => setThemeMode(themeMode === "dark" ? "light" : "dark")}
            >
              {themeMode === "dark" ? <LightModeRoundedIcon fontSize="small" /> : <DarkModeRoundedIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Open workspace">
            <IconButton
              size="small"
              aria-label="Open workspace"
              onClick={() => openWorkspace({})}
            >
              <RssFeedRoundedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Box className="settings-workspace-main">{children}</Box>
      </Box>
    </Box>
  );
}
