import AddLinkRoundedIcon from "@mui/icons-material/AddLinkRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import CreateNewFolderRoundedIcon from "@mui/icons-material/CreateNewFolderRounded";
import DynamicFeedRoundedIcon from "@mui/icons-material/DynamicFeedRounded";
import ExtensionRoundedIcon from "@mui/icons-material/ExtensionRounded";
import FolderRoundedIcon from "@mui/icons-material/FolderRounded";
import MoreHorizRoundedIcon from "@mui/icons-material/MoreHorizRounded";
import TravelExploreRoundedIcon from "@mui/icons-material/TravelExploreRounded";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  List,
  ListItemButton,
  ListItemText,
  Menu,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";

import type { NavigationHierarchy } from "../../../entities/navigation/model";
import type { FeedFolder, PluginArea } from "../../../shared/types/contracts";
import { getFeedAvatarHue, getFeedInitial } from "../lib/feedIcons";
import {
  loadExpandedFolderIds,
  loadMonitoringExpanded,
  saveExpandedFolderIds,
  saveMonitoringExpanded,
} from "../lib/navState";

type NavigationPaneProps = {
  isReadOnly: boolean;
  density: "compact" | "comfortable";
  navPreset: "tight" | "balanced" | "airy";
  hierarchy: NavigationHierarchy | null;
  folders: FeedFolder[];
  feedIconByFeedId: Record<string, string | null>;
  selectedScopeType: string;
  selectedScopeKey: string;
  isLoading: boolean;
  isError: boolean;
  onSelectSystem: (systemKey: string) => void;
  onSelectFolder: (folderId: string) => void;
  onSelectFeed: (feedId: string) => void;
  onSelectStream: (streamId: string) => void;
  pluginAreas: PluginArea[];
  selectedPluginAreaRouteKey: string | null;
  onSelectPluginArea: (area: PluginArea) => void;
  onCreateFolder: (name: string) => Promise<void>;
  onCreateFeed: (payload: { title: string; url: string; folderId: string | null }) => Promise<void>;
  onRenameFolder: (folderId: string, name: string) => Promise<void>;
  onDeleteFolder: (folderId: string) => Promise<void>;
  onAssignFeedFolder: (feedId: string, folderId: string | null) => Promise<void>;
  isFolderMutationPending: boolean;
  isFeedMutationPending: boolean;
  isAssignPending: boolean;
};

type FeedMenuState = { anchor: HTMLElement; feedId: string } | null;
type FolderActionMenuState = { anchor: HTMLElement; folderId: string; folderName: string } | null;
type InitialFolderState = {
  hasPreference: boolean;
  map: Record<string, boolean>;
};

function getInitialFolderState(): InitialFolderState {
  const stored = loadExpandedFolderIds();
  if (!stored) {
    return { hasPreference: false, map: {} };
  }
  return {
    hasPreference: true,
    map: Object.fromEntries(Array.from(stored).map((folderId) => [folderId, true])),
  };
}

function getExpandedFolderIds(expandedFolders: Record<string, boolean>): Set<string> {
  return new Set(
    Object.entries(expandedFolders)
      .filter(([, isExpanded]) => isExpanded)
      .map(([folderId]) => folderId)
  );
}

function pluginAreaIcon(icon: string | null | undefined) {
  const iconKey = (icon ?? "").toLowerCase();
  if (iconKey === "search") {
    return <TravelExploreRoundedIcon fontSize="inherit" className="workspace-nav__plugin-icon" />;
  }
  if (iconKey === "rss") {
    return <DynamicFeedRoundedIcon fontSize="inherit" className="workspace-nav__plugin-icon" />;
  }
  return <ExtensionRoundedIcon fontSize="inherit" className="workspace-nav__plugin-icon" />;
}

export function NavigationPane({
  isReadOnly,
  density,
  navPreset,
  hierarchy,
  folders,
  feedIconByFeedId,
  selectedScopeType,
  selectedScopeKey,
  isLoading,
  isError,
  onSelectSystem,
  onSelectFolder,
  onSelectFeed,
  onSelectStream,
  pluginAreas,
  selectedPluginAreaRouteKey,
  onSelectPluginArea,
  onCreateFolder,
  onCreateFeed,
  onRenameFolder,
  onDeleteFolder,
  onAssignFeedFolder,
  isFolderMutationPending,
  isFeedMutationPending,
  isAssignPending,
}: NavigationPaneProps) {
  const [initialFolderState] = useState(getInitialFolderState);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>(initialFolderState.map);
  const [hasExpansionPreference, setHasExpansionPreference] = useState(initialFolderState.hasPreference);
  const [createOpen, setCreateOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [folderNameInput, setFolderNameInput] = useState("");
  const [activeFolderId, setActiveFolderId] = useState("");
  const [activeFolderName, setActiveFolderName] = useState("");
  const [feedMenu, setFeedMenu] = useState<FeedMenuState>(null);
  const [folderMenu, setFolderMenu] = useState<FolderActionMenuState>(null);
  const [failedFeedIcons, setFailedFeedIcons] = useState<Record<string, true>>({});
  const [monitoringExpanded, setMonitoringExpanded] = useState(() => loadMonitoringExpanded() ?? true);
  const [localError, setLocalError] = useState<string | null>(null);
  const [expandedMonitoringFolders, setExpandedMonitoringFolders] = useState<Record<string, boolean>>({});
  const [createFeedOpen, setCreateFeedOpen] = useState(false);
  const [feedUrlInput, setFeedUrlInput] = useState("");
  const [feedTitleInput, setFeedTitleInput] = useState("");
  const [feedFolderIdInput, setFeedFolderIdInput] = useState("");
  const [feedCreateError, setFeedCreateError] = useState<string | null>(null);

  const folderOptions = useMemo(
    () => [{ id: null, name: "Unfiled" }, ...folders.map((folder) => ({ id: folder.id, name: folder.name }))],
    [folders]
  );
  const folderKeys = useMemo(
    () => (hierarchy ? hierarchy.folders.map((folder) => folder.scope_id || "unfiled") : []),
    [hierarchy]
  );
  const defaultFolderOpen = !hasExpansionPreference;

  const isFolderOpen = (folderKey: string): boolean => {
    const current = expandedFolders[folderKey];
    if (current !== undefined) {
      return current;
    }
    return defaultFolderOpen;
  };

  const allFoldersExpanded = folderKeys.length > 0 && folderKeys.every((folderKey) => isFolderOpen(folderKey));

  const toggleFolder = (folderKey: string) => {
    setHasExpansionPreference(true);
    setExpandedFolders((previous) => {
      const current = previous[folderKey] ?? defaultFolderOpen;
      const next = { ...previous, [folderKey]: !current };
      saveExpandedFolderIds(getExpandedFolderIds(next));
      return next;
    });
  };

  const expandAllFolders = () => {
    const next = Object.fromEntries(folderKeys.map((folderKey) => [folderKey, true]));
    setHasExpansionPreference(true);
    setExpandedFolders(next);
    saveExpandedFolderIds(new Set(folderKeys));
  };

  const collapseAllFolders = () => {
    setHasExpansionPreference(true);
    setExpandedFolders({});
    saveExpandedFolderIds(new Set());
  };

  const toggleMonitoringSection = () => {
    setMonitoringExpanded((previous) => {
      const next = !previous;
      saveMonitoringExpanded(next);
      return next;
    });
  };

  const isMonitoringFolderOpen = (folderKey: string): boolean => expandedMonitoringFolders[folderKey] ?? true;

  const toggleMonitoringFolder = (folderKey: string) => {
    setExpandedMonitoringFolders((previous) => ({
      ...previous,
      [folderKey]: !isMonitoringFolderOpen(folderKey),
    }));
  };

  const closeDialogs = () => {
    setCreateOpen(false);
    setRenameOpen(false);
    setDeleteOpen(false);
    setFolderNameInput("");
    setActiveFolderId("");
    setActiveFolderName("");
    setLocalError(null);
  };

  const closeCreateFeedDialog = () => {
    setCreateFeedOpen(false);
    setFeedUrlInput("");
    setFeedTitleInput("");
    setFeedFolderIdInput("");
    setFeedCreateError(null);
  };

  const submitCreate = async () => {
    try {
      await onCreateFolder(folderNameInput);
      closeDialogs();
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Failed to create folder.");
    }
  };

  const submitCreateFeed = async () => {
    setFeedCreateError(null);

    const url = feedUrlInput.trim();
    if (!url) {
      setFeedCreateError("Feed URL is required.");
      return;
    }
    try {
      new URL(url);
    } catch {
      setFeedCreateError("Feed URL must be a valid URL.");
      return;
    }

    try {
      await onCreateFeed({
        title: feedTitleInput.trim() || url,
        url,
        folderId: feedFolderIdInput.length > 0 ? feedFolderIdInput : null,
      });
      closeCreateFeedDialog();
    } catch (error) {
      setFeedCreateError(error instanceof Error ? error.message : "Failed to create feed.");
    }
  };

  const submitRename = async () => {
    try {
      await onRenameFolder(activeFolderId, folderNameInput);
      closeDialogs();
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Failed to rename folder.");
    }
  };

  const submitDelete = async () => {
    try {
      await onDeleteFolder(activeFolderId);
      closeDialogs();
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Failed to delete folder.");
    }
  };

  return (
    <Paper className={`workspace-nav workspace-nav--preset-${navPreset}`} component="section" elevation={0}>
      <Stack sx={{ mb: 1 }} className="workspace-nav__toolbar">
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Feeds</Typography>
          {!isReadOnly ? (
            <Stack direction="row" spacing={0.4}>
              <Tooltip title="Add feed">
                <IconButton size="small" aria-label="Add feed" onClick={() => setCreateFeedOpen(true)}>
                  <AddLinkRoundedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="Add folder">
                <IconButton size="small" aria-label="Add folder" onClick={() => setCreateOpen(true)}>
                  <CreateNewFolderRoundedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
          ) : null}
        </Stack>
      </Stack>

      {isLoading ? <Typography color="text.secondary">Loading navigation...</Typography> : null}
      {isError ? <Alert severity="error">Failed to load navigation.</Alert> : null}

      {hierarchy ? (
        <Stack spacing={1.5}>
          <Box className="workspace-nav__section">
            <Typography className="workspace-nav__section-title">System</Typography>
            <List dense={density === "compact"} disablePadding>
              {hierarchy.systems.map((item) => (
                <ListItemButton
                  key={item.scope_id}
                  selected={selectedScopeType === "system" && selectedScopeKey === item.scope_id}
                  onClick={() => onSelectSystem(item.scope_id)}
                  className="workspace-nav__row"
                >
                  <ListItemText primary={item.title} />
                  <Typography variant="caption" color="primary" className="workspace-nav__count">
                    {item.unread_count}
                  </Typography>
                </ListItemButton>
              ))}
            </List>
          </Box>

          <Box className="workspace-nav__section">
            <Stack direction="row" justifyContent="space-between" alignItems="center" className="workspace-nav__section-header">
              <Typography className="workspace-nav__section-title">Monitoring feeds</Typography>
              <IconButton
                size="small"
                aria-label={`${monitoringExpanded ? "Collapse" : "Expand"} monitoring feeds`}
                onClick={toggleMonitoringSection}
              >
                <ChevronRightRoundedIcon
                  className={`workspace-nav__section-chevron${monitoringExpanded ? " workspace-nav__section-chevron--open" : ""}`}
                  fontSize="small"
                />
              </IconButton>
            </Stack>
            <Collapse in={monitoringExpanded} timeout="auto" unmountOnExit>
              <Stack spacing={0.2}>
                {hierarchy.monitoring_folders
                  .filter((monitoringFolder) => monitoringFolder.streams.length > 0)
                  .map((monitoringFolder) => {
                    const folderKey = monitoringFolder.id ?? "unfiled-monitoring";
                    const open = isMonitoringFolderOpen(folderKey);
                    return (
                      <Box key={folderKey}>
                        <Stack direction="row" alignItems="center" className="workspace-nav__item-group">
                          <IconButton
                            size="small"
                            aria-label={`${open ? "Collapse" : "Expand"} monitoring folder ${monitoringFolder.name}`}
                            className="workspace-nav__folder-toggle"
                            onClick={(event) => {
                              event.preventDefault();
                              event.stopPropagation();
                              toggleMonitoringFolder(folderKey);
                            }}
                          >
                            <ChevronRightRoundedIcon
                              className={`workspace-nav__folder-icon${open ? " workspace-nav__folder-icon--open" : ""}`}
                              fontSize="small"
                            />
                          </IconButton>
                          <Stack direction="row" alignItems="center" className="workspace-nav__row workspace-nav__row--folder">
                            <Box className="workspace-nav__folder-label">
                              <FolderRoundedIcon fontSize="inherit" className="workspace-nav__folder-inline-icon" />
                              <ListItemText primary={monitoringFolder.name} />
                            </Box>
                            <Typography variant="caption" color="text.secondary" className="workspace-nav__count">
                              {monitoringFolder.unread_count}
                            </Typography>
                          </Stack>
                        </Stack>
                        <Collapse in={open} timeout="auto" unmountOnExit>
                          <List dense={density === "compact"} disablePadding className="workspace-nav__children">
                            {monitoringFolder.streams.map((stream) => (
                              <ListItemButton
                                key={stream.scope_id}
                                selected={selectedScopeType === "stream" && selectedScopeKey === stream.scope_id}
                                onClick={() => onSelectStream(stream.scope_id)}
                                className="workspace-nav__row"
                              >
                                <ListItemText primary={stream.name} />
                                <Typography variant="caption" color="text.secondary" className="workspace-nav__count">
                                  {stream.unread_count}
                                </Typography>
                              </ListItemButton>
                            ))}
                          </List>
                        </Collapse>
                      </Box>
                    );
                  })}
              </Stack>
            </Collapse>
          </Box>

          {pluginAreas.length > 0 ? (
            <Box className="workspace-nav__section">
              <Typography className="workspace-nav__section-title">Plugins</Typography>
              <List dense={density === "compact"} disablePadding>
                {pluginAreas.map((pluginArea) => (
                  <ListItemButton
                    key={pluginArea.id}
                    selected={selectedPluginAreaRouteKey === pluginArea.route_key}
                    onClick={() => onSelectPluginArea(pluginArea)}
                    className="workspace-nav__row"
                  >
                    <Box className="workspace-nav__plugin-label">
                      {pluginAreaIcon(pluginArea.icon)}
                      <ListItemText primary={pluginArea.title} />
                    </Box>
                  </ListItemButton>
                ))}
              </List>
            </Box>
          ) : null}

          <Box className="workspace-nav__section">
            <Stack direction="row" justifyContent="space-between" alignItems="center" className="workspace-nav__section-header">
              <Typography className="workspace-nav__section-title">Folders</Typography>
              <IconButton
                size="small"
                aria-label={allFoldersExpanded ? "Collapse all folders" : "Expand all folders"}
                onClick={allFoldersExpanded ? collapseAllFolders : expandAllFolders}
              >
                <ChevronRightRoundedIcon
                  className={`workspace-nav__section-chevron${allFoldersExpanded ? " workspace-nav__section-chevron--open" : ""}`}
                  fontSize="small"
                />
              </IconButton>
            </Stack>
            <List dense={density === "compact"} disablePadding>
              {hierarchy.folders.map((folder) => {
                const folderKey = folder.scope_id || "unfiled";
                const open = isFolderOpen(folderKey);
                const selectable = !folder.is_unfiled && folder.scope_id.length > 0;
                const folderSelected = selectable && selectedScopeType === "folder" && selectedScopeKey === folder.scope_id;

                return (
                  <Box key={folderKey}>
                    <Stack
                      direction="row"
                      alignItems="center"
                      className={`workspace-nav__item-group workspace-nav__item-group--folder${
                        folderSelected ? " workspace-nav__item-group--selected" : ""
                      }`}
                    >
                      <IconButton
                        size="small"
                        aria-label={`${open ? "Collapse" : "Expand"} folder ${folder.name}`}
                        className="workspace-nav__folder-toggle"
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          toggleFolder(folderKey);
                        }}
                      >
                        <ChevronRightRoundedIcon
                          className={`workspace-nav__folder-icon${open ? " workspace-nav__folder-icon--open" : ""}`}
                          fontSize="small"
                        />
                      </IconButton>
                      <ListItemButton
                        selected={folderSelected}
                        aria-label={`Folder ${folder.name}`}
                        onClick={() => {
                          if (selectable) {
                            onSelectFolder(folder.scope_id);
                          }
                        }}
                        className="workspace-nav__row workspace-nav__row--folder"
                      >
                        <Box className="workspace-nav__folder-label">
                          <ListItemText primary={folder.name} />
                        </Box>
                        <Typography variant="caption" color="text.secondary" className="workspace-nav__count">
                          {folder.unread_count}
                        </Typography>
                      </ListItemButton>
                      {!isReadOnly && !folder.is_unfiled ? (
                        <IconButton
                          size="small"
                          className="workspace-nav__action-button"
                          aria-label={`Folder actions for ${folder.name}`}
                          onClick={(event) =>
                            setFolderMenu({ anchor: event.currentTarget, folderId: folder.scope_id, folderName: folder.name })
                          }
                        >
                          <MoreHorizRoundedIcon fontSize="small" />
                        </IconButton>
                      ) : null}
                    </Stack>

                    <Collapse in={open} timeout="auto" unmountOnExit>
                      <List dense={density === "compact"} disablePadding className="workspace-nav__children">
                        {folder.feeds.map((feed) => (
                          <FeedRow
                            key={feed.id}
                            feed={feed}
                            feedIconByFeedId={feedIconByFeedId}
                            failedFeedIcons={failedFeedIcons}
                            selectedScopeKey={selectedScopeKey}
                            selectedScopeType={selectedScopeType}
                            density={density}
                            setFailedFeedIcons={setFailedFeedIcons}
                            onSelectFeed={onSelectFeed}
                            isReadOnly={isReadOnly}
                            onOpenFeedMenu={(event) => setFeedMenu({ anchor: event.currentTarget, feedId: feed.id })}
                          />
                        ))}
                      </List>
                    </Collapse>
                  </Box>
                );
              })}
            </List>
          </Box>

        </Stack>
      ) : null}

      {!isReadOnly ? (
        <>
          <Menu
            open={feedMenu !== null}
            anchorEl={feedMenu?.anchor ?? null}
            onClose={() => setFeedMenu(null)}
          >
            {folderOptions.map((folderOption) => (
              <MenuItem
                key={folderOption.id ?? "unfiled"}
                disabled={isAssignPending}
                onClick={() => {
                  void (async () => {
                    if (!feedMenu) {
                      return;
                    }
                    await onAssignFeedFolder(feedMenu.feedId, folderOption.id);
                    setFeedMenu(null);
                  })();
                }}
              >
                Move to {folderOption.name}
              </MenuItem>
            ))}
          </Menu>

          <Menu
            open={folderMenu !== null}
            anchorEl={folderMenu?.anchor ?? null}
            onClose={() => setFolderMenu(null)}
          >
            <MenuItem
              onClick={() => {
                if (!folderMenu) {
                  return;
                }
                setActiveFolderId(folderMenu.folderId);
                setActiveFolderName(folderMenu.folderName);
                setFolderNameInput(folderMenu.folderName);
                setRenameOpen(true);
                setFolderMenu(null);
              }}
            >
              Rename folder
            </MenuItem>
            <MenuItem
              onClick={() => {
                if (!folderMenu) {
                  return;
                }
                setActiveFolderId(folderMenu.folderId);
                setActiveFolderName(folderMenu.folderName);
                setDeleteOpen(true);
                setFolderMenu(null);
              }}
            >
              Delete folder
            </MenuItem>
          </Menu>

          <Dialog open={createOpen} onClose={closeDialogs}>
            <DialogTitle>Create folder</DialogTitle>
            <DialogContent>
              {localError ? <Alert severity="error">{localError}</Alert> : null}
              <TextField
                margin="dense"
                autoFocus
                fullWidth
                label="Folder name"
                value={folderNameInput}
                onChange={(event) => setFolderNameInput(event.target.value)}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={closeDialogs}>Cancel</Button>
              <Button onClick={() => void submitCreate()} disabled={isFolderMutationPending}>
                Create
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog open={createFeedOpen} onClose={closeCreateFeedDialog}>
            <DialogTitle>Add feed</DialogTitle>
            <DialogContent>
              <Stack spacing={1.2} sx={{ mt: 0.4, minWidth: { xs: 260, sm: 380 } }}>
                {feedCreateError ? <Alert severity="error">{feedCreateError}</Alert> : null}
                <TextField
                  margin="dense"
                  autoFocus
                  fullWidth
                  required
                  label="Feed URL"
                  value={feedUrlInput}
                  onChange={(event) => setFeedUrlInput(event.target.value)}
                  placeholder="https://example.com/rss"
                />
                <TextField
                  margin="dense"
                  fullWidth
                  label="Title (optional)"
                  value={feedTitleInput}
                  onChange={(event) => setFeedTitleInput(event.target.value)}
                />
                <FormControl size="small">
                  <InputLabel id="nav-create-feed-folder-label">Folder</InputLabel>
                  <Select
                    labelId="nav-create-feed-folder-label"
                    label="Folder"
                    value={feedFolderIdInput}
                    onChange={(event) => setFeedFolderIdInput(event.target.value)}
                  >
                    <MenuItem value="">Unfiled</MenuItem>
                    {folders.map((folder) => (
                      <MenuItem key={folder.id} value={folder.id}>
                        {folder.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={closeCreateFeedDialog}>Cancel</Button>
              <Button variant="contained" onClick={() => void submitCreateFeed()} disabled={isFeedMutationPending}>
                Add feed
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog open={renameOpen} onClose={closeDialogs}>
            <DialogTitle>Rename folder</DialogTitle>
            <DialogContent>
              {localError ? <Alert severity="error">{localError}</Alert> : null}
              <TextField
                margin="dense"
                autoFocus
                fullWidth
                label="Folder name"
                value={folderNameInput}
                onChange={(event) => setFolderNameInput(event.target.value)}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={closeDialogs}>Cancel</Button>
              <Button onClick={() => void submitRename()} disabled={isFolderMutationPending}>
                Save
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog open={deleteOpen} onClose={closeDialogs}>
            <DialogTitle>Delete folder</DialogTitle>
            <DialogContent>
              {localError ? <Alert severity="error">{localError}</Alert> : null}
              <Typography variant="body2">Delete folder "{activeFolderName}"? Feeds will be moved to Unfiled.</Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={closeDialogs}>Cancel</Button>
              <Button color="error" onClick={() => void submitDelete()} disabled={isFolderMutationPending}>
                Delete
              </Button>
            </DialogActions>
          </Dialog>
        </>
      ) : null}
    </Paper>
  );
}

type FeedRowProps = {
  feed: NavigationHierarchy["folders"][number]["feeds"][number];
  feedIconByFeedId: Record<string, string | null>;
  failedFeedIcons: Record<string, true>;
  density: "compact" | "comfortable";
  isReadOnly: boolean;
  selectedScopeType: string;
  selectedScopeKey: string;
  onSelectFeed: (feedId: string) => void;
  onOpenFeedMenu: (event: React.MouseEvent<HTMLElement>) => void;
  setFailedFeedIcons: React.Dispatch<React.SetStateAction<Record<string, true>>>;
};

function FeedRow({
  feed,
  feedIconByFeedId,
  failedFeedIcons,
  density,
  isReadOnly,
  selectedScopeType,
  selectedScopeKey,
  onSelectFeed,
  onOpenFeedMenu,
  setFailedFeedIcons,
}: FeedRowProps) {
  const feedIconSrc = failedFeedIcons[feed.id] ? null : (feedIconByFeedId[feed.id] ?? null);
  const feedAvatarHue = getFeedAvatarHue(feed.title);
  const feedAvatarSize = density === "comfortable" ? 16 : 14;
  const isSelected = selectedScopeType === "feed" && selectedScopeKey === feed.scope_id;

  return (
    <Stack
      direction="row"
      alignItems="center"
      className={`workspace-nav__item-group workspace-nav__item-group--feed${
        isSelected ? " workspace-nav__item-group--selected" : ""
      }`}
    >
      <ListItemButton
        selected={isSelected}
        onClick={() => onSelectFeed(String(feed.scope_id))}
        className="workspace-nav__row workspace-nav__row--feed"
      >
        <Box className="workspace-nav__feed-label">
          <Avatar
            className="workspace-nav__feed-avatar"
            alt={feed.title}
            imgProps={{
              loading: "lazy",
              referrerPolicy: "no-referrer",
              onError: () => {
                setFailedFeedIcons((previous) => ({ ...previous, [feed.id]: true }));
              },
            }}
            sx={{
              width: feedAvatarSize,
              height: feedAvatarSize,
              fontSize: feedAvatarSize <= 14 ? "0.56rem" : "0.62rem",
              bgcolor: `hsl(${feedAvatarHue} 45% 90%)`,
              color: `hsl(${feedAvatarHue} 45% 28%)`,
            }}
            {...(feedIconSrc ? { src: feedIconSrc } : {})}
          >
            {getFeedInitial(feed.title)}
          </Avatar>
          <ListItemText primary={feed.title} />
        </Box>
        <Typography variant="caption" color="text.secondary" className="workspace-nav__count">
          {feed.unread_count}
        </Typography>
      </ListItemButton>
      {!isReadOnly ? (
        <IconButton
          size="small"
          className="workspace-nav__action-button"
          aria-label={`Feed actions for ${feed.title}`}
          onClick={onOpenFeedMenu}
        >
          <MoreHorizRoundedIcon fontSize="small" />
        </IconButton>
      ) : null}
    </Stack>
  );
}
