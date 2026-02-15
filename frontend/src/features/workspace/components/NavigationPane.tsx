import {
  Alert,
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

type NavigationPaneProps = {
  density: "compact" | "comfortable";
  hierarchy: NavigationHierarchy | null;
  folders: FeedFolder[];
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

export function NavigationPane({
  density,
  hierarchy,
  folders,
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
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const [createOpen, setCreateOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [folderNameInput, setFolderNameInput] = useState("");
  const [activeFolderId, setActiveFolderId] = useState("");
  const [activeFolderName, setActiveFolderName] = useState("");
  const [feedMenu, setFeedMenu] = useState<FeedMenuState>(null);
  const [folderMenu, setFolderMenu] = useState<FolderActionMenuState>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const folderOptions = useMemo(
    () => [{ id: null, name: "Unfiled" }, ...folders.map((folder) => ({ id: folder.id, name: folder.name }))],
    [folders]
  );

  const toggleFolder = (folderKey: string) => {
    setExpandedFolders((previous) => ({ ...previous, [folderKey]: !previous[folderKey] }));
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
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
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
          <Button size="small" variant="outlined" onClick={() => setCreateOpen(true)}>
            + Folder
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
                  <Typography variant="caption" color="primary">
                    {item.unread_count}
                  </Typography>
                </ListItemButton>
              ))}
            </List>
          </Box>

          <Box>
            <Typography className="workspace-nav__section-title">Folders</Typography>
            <List dense={density === "compact"} disablePadding>
              {hierarchy.folders.map((folder) => {
                const folderKey = folder.scope_id || "unfiled";
                const open = expandedFolders[folderKey] ?? true;
                const selectable = !folder.is_unfiled && folder.scope_id.length > 0;

                return (
                  <Box key={folderKey}>
                    <Stack direction="row" alignItems="center">
                      <ListItemButton
                        selected={selectable && selectedScopeType === "folder" && selectedScopeKey === folder.scope_id}
                        onClick={() => {
                          if (selectable) {
                            onSelectFolder(folder.scope_id);
                          }
                          toggleFolder(folderKey);
                        }}
                        className="workspace-nav__row workspace-nav__row--folder"
                      >
                        <ListItemText primary={`${open ? "▾" : "▸"} ${folder.name}`} />
                        <Typography variant="caption" color="text.secondary">
                          {folder.unread_count}
                        </Typography>
                      </ListItemButton>
                      {!folder.is_unfiled ? (
                        <IconButton
                          size="small"
                          onClick={(event) =>
                            setFolderMenu({ anchor: event.currentTarget, folderId: folder.scope_id, folderName: folder.name })
                          }
                        >
                          ⋯
                        </IconButton>
                      ) : null}
                    </Stack>

                    <Collapse in={open} timeout="auto" unmountOnExit>
                      <List dense={density === "compact"} disablePadding className="workspace-nav__children">
                        {folder.feeds.map((feed) => (
                          <Stack key={feed.id} direction="row" alignItems="center">
                            <ListItemButton
                              selected={selectedScopeType === "feed" && selectedScopeKey === feed.scope_id}
                              onClick={() => onSelectFeed(String(feed.scope_id))}
                              className="workspace-nav__row workspace-nav__row--feed"
                            >
                              <ListItemText primary={feed.title} />
                              <Typography variant="caption" color="text.secondary">
                                {feed.unread_count}
                              </Typography>
                            </ListItemButton>
                            <IconButton
                              size="small"
                              onClick={(event) => setFeedMenu({ anchor: event.currentTarget, feedId: feed.id })}
                            >
                              ⋯
                            </IconButton>
                          </Stack>
                        ))}
                      </List>
                    </Collapse>
                  </Box>
                );
              })}
            </List>
          </Box>

          <Box>
            <Typography className="workspace-nav__section-title">Monitoring feeds</Typography>
            <List dense={density === "compact"} disablePadding>
              {hierarchy.streams.map((stream) => (
                <ListItemButton
                  key={stream.scope_id}
                  selected={selectedScopeType === "stream" && selectedScopeKey === stream.scope_id}
                  onClick={() => onSelectStream(stream.scope_id)}
                  className="workspace-nav__row"
                >
                  <ListItemText primary={stream.name} />
                  <Typography variant="caption" color="text.secondary">
                    {stream.unread_count}
                  </Typography>
                </ListItemButton>
              ))}
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
