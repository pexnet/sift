import AddRoundedIcon from "@mui/icons-material/AddRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import MoreHorizRoundedIcon from "@mui/icons-material/MoreHorizRounded";
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
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";

import type { NavigationHierarchy } from "../../../entities/navigation/model";
import type { FeedFolder } from "../../../shared/types/contracts";
import { getFeedAvatarHue, getFeedInitial } from "../lib/feedIcons";
import {
  loadExpandedFolderIds,
  loadMonitoringExpanded,
  saveExpandedFolderIds,
  saveMonitoringExpanded,
} from "../lib/navState";

type NavigationPaneProps = {
  density: "compact" | "comfortable";
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
  onCreateFolder: (name: string) => Promise<void>;
  onRenameFolder: (folderId: string, name: string) => Promise<void>;
  onDeleteFolder: (folderId: string) => Promise<void>;
  onAssignFeedFolder: (feedId: string, folderId: string | null) => Promise<void>;
  isFolderMutationPending: boolean;
  isAssignPending: boolean;
  onToggleTheme: () => void;
  themeMode: "light" | "dark";
  onDensityChange: (value: "compact" | "comfortable") => void;
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

export function NavigationPane({
  density,
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
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  onAssignFeedFolder,
  isFolderMutationPending,
  isAssignPending,
  onToggleTheme,
  themeMode,
  onDensityChange,
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

  const closeDialogs = () => {
    setCreateOpen(false);
    setRenameOpen(false);
    setDeleteOpen(false);
    setFolderNameInput("");
    setActiveFolderId("");
    setActiveFolderName("");
    setLocalError(null);
  };

  const submitCreate = async () => {
    try {
      await onCreateFolder(folderNameInput);
      closeDialogs();
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Failed to create folder.");
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
    <Paper className="workspace-nav" component="section" elevation={0}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }} className="workspace-nav__toolbar">
        <Typography variant="h6">Feeds</Typography>
        <Stack direction="row" spacing={0.5}>
          <Button size="small" variant="text" onClick={onToggleTheme}>
            {themeMode === "dark" ? "Light" : "Dark"}
          </Button>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel id="density-select">Density</InputLabel>
            <Select
              labelId="density-select"
              label="Density"
              value={density}
              onChange={(event) =>
                onDensityChange(event.target.value === "comfortable" ? "comfortable" : "compact")
              }
            >
              <MenuItem value="compact">Compact</MenuItem>
              <MenuItem value="comfortable">Comfortable</MenuItem>
            </Select>
          </FormControl>
          <Button size="small" variant="outlined" onClick={() => setCreateOpen(true)} startIcon={<AddRoundedIcon />}>
            Folder
          </Button>
        </Stack>
      </Stack>

      {isLoading ? <Typography color="text.secondary">Loading navigation...</Typography> : null}
      {isError ? <Alert severity="error">Failed to load navigation.</Alert> : null}

      {hierarchy ? (
        <Stack spacing={1.5}>
          <Box>
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

          <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography className="workspace-nav__section-title">Monitoring feeds</Typography>
              <IconButton
                size="small"
                className="workspace-nav__section-toggle"
                aria-label={`${monitoringExpanded ? "Collapse" : "Expand"} monitoring feeds`}
                onClick={toggleMonitoringSection}
              >
                {monitoringExpanded ? <ExpandMoreRoundedIcon fontSize="small" /> : <ChevronRightRoundedIcon fontSize="small" />}
              </IconButton>
            </Stack>
            <Collapse in={monitoringExpanded} timeout="auto" unmountOnExit>
              <List dense={density === "compact"} disablePadding>
                {hierarchy.streams.map((stream) => (
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

          <Box>
            <Typography className="workspace-nav__section-title">Folders</Typography>
            <Stack direction="row" spacing={0.5} sx={{ px: 0.5, pb: 0.5 }}>
              <Button size="small" variant="text" onClick={expandAllFolders}>
                Expand all
              </Button>
              <Button size="small" variant="text" onClick={collapseAllFolders}>
                Collapse all
              </Button>
            </Stack>
            <List dense={density === "compact"} disablePadding>
              {hierarchy.folders.map((folder) => {
                const folderKey = folder.scope_id || "unfiled";
                const open = isFolderOpen(folderKey);
                const selectable = !folder.is_unfiled && folder.scope_id.length > 0;

                return (
                  <Box key={folderKey}>
                    <Stack direction="row" alignItems="center">
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
                        {open ? (
                          <ExpandMoreRoundedIcon className="workspace-nav__folder-icon" fontSize="small" />
                        ) : (
                          <ChevronRightRoundedIcon className="workspace-nav__folder-icon" fontSize="small" />
                        )}
                      </IconButton>
                      <ListItemButton
                        selected={selectable && selectedScopeType === "folder" && selectedScopeKey === folder.scope_id}
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
                      {!folder.is_unfiled ? (
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
    </Paper>
  );
}

type FeedRowProps = {
  feed: NavigationHierarchy["folders"][number]["feeds"][number];
  feedIconByFeedId: Record<string, string | null>;
  failedFeedIcons: Record<string, true>;
  density: "compact" | "comfortable";
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
  selectedScopeType,
  selectedScopeKey,
  onSelectFeed,
  onOpenFeedMenu,
  setFailedFeedIcons,
}: FeedRowProps) {
  const feedIconSrc = failedFeedIcons[feed.id] ? null : (feedIconByFeedId[feed.id] ?? null);
  const feedAvatarHue = getFeedAvatarHue(feed.title);
  const feedAvatarSize = density === "comfortable" ? 16 : 14;

  return (
    <Stack direction="row" alignItems="center">
      <ListItemButton
        selected={selectedScopeType === "feed" && selectedScopeKey === feed.scope_id}
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
      <IconButton
        size="small"
        className="workspace-nav__action-button"
        aria-label={`Feed actions for ${feed.title}`}
        onClick={onOpenFeedMenu}
      >
        <MoreHorizRoundedIcon fontSize="small" />
      </IconButton>
    </Stack>
  );
}
