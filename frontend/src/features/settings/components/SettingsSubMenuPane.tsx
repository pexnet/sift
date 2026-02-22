import { List, ListItemButton, ListItemText, Paper, Stack, Typography } from "@mui/material";

type SettingsSectionId = "general" | "feed-health" | "monitoring" | "help";

type SettingsSubMenuPaneProps = {
  density: "compact" | "comfortable";
  navPreset: "tight" | "balanced" | "airy";
  activeSection: SettingsSectionId;
  onSelect: (path: "/account" | "/account/feed-health" | "/account/monitoring" | "/help") => void;
};

const SETTINGS_SECTIONS: Array<{ id: SettingsSectionId; title: string; path: "/account" | "/account/feed-health" | "/account/monitoring" | "/help" }> = [
  { id: "general", title: "General", path: "/account" },
  { id: "feed-health", title: "Feed health", path: "/account/feed-health" },
  { id: "monitoring", title: "Monitoring feeds", path: "/account/monitoring" },
  { id: "help", title: "Help", path: "/help" },
];

export function SettingsSubMenuPane({ density, navPreset, activeSection, onSelect }: SettingsSubMenuPaneProps) {
  return (
    <Paper className={`workspace-nav workspace-nav--preset-${navPreset}`} component="aside" elevation={0} aria-label="Settings navigation">
      <Stack sx={{ mb: 1 }} className="workspace-nav__toolbar">
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Settings</Typography>
        </Stack>
      </Stack>

      <Stack spacing={1.5}>
        <Typography className="workspace-nav__section-title">Preferences</Typography>
        <List dense={density === "compact"} disablePadding>
          {SETTINGS_SECTIONS.map((section) => (
            <ListItemButton
              key={section.id}
              selected={activeSection === section.id}
              onClick={() => onSelect(section.path)}
              className="workspace-nav__row"
              aria-label={section.title}
            >
              <ListItemText primary={section.title} />
            </ListItemButton>
          ))}
        </List>
      </Stack>
    </Paper>
  );
}
