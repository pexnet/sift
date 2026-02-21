import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

type SettingsSectionId = "general" | "feed-health" | "monitoring" | "help";

type SettingsLayoutProps = {
  activeSection: SettingsSectionId;
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  headingId?: string;
  maxWidth?: number;
};

const SETTINGS_NAV_ITEMS: Array<{ id: SettingsSectionId; label: string; href: string }> = [
  { id: "general", label: "General", href: "/account" },
  { id: "feed-health", label: "Feed health", href: "/account/feed-health" },
  { id: "monitoring", label: "Monitoring feeds", href: "/account/monitoring" },
  { id: "help", label: "Help", href: "/help" },
];

export function SettingsLayout({
  activeSection,
  title,
  description,
  actions,
  children,
  headingId,
  maxWidth = 1200,
}: SettingsLayoutProps) {
  const resolvedHeadingId = headingId ?? "settings-page-heading";

  return (
    <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ maxWidth, mx: "auto", width: "100%" }}>
      <Paper
        component="aside"
        variant="outlined"
        sx={{
          p: 1.2,
          alignSelf: { xs: "stretch", md: "flex-start" },
          flex: "0 0 220px",
        }}
        aria-label="Settings navigation"
      >
        <Stack spacing={0.8}>
          <Typography component="p" variant="subtitle2" color="text.secondary" sx={{ px: 0.5 }}>
            Settings
          </Typography>
          {SETTINGS_NAV_ITEMS.map((item) => (
            <Button
              key={item.id}
              component="a"
              href={item.href}
              fullWidth
              size="small"
              variant={activeSection === item.id ? "contained" : "text"}
              sx={{ justifyContent: "flex-start" }}
            >
              {item.label}
            </Button>
          ))}
        </Stack>
      </Paper>

      <Paper
        component="section"
        className="panel settings-panel"
        sx={{ flex: "1 1 auto", maxWidth: "unset" }}
        aria-labelledby={resolvedHeadingId}
      >
        <Stack spacing={2.2}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ xs: "stretch", sm: "center" }}
            spacing={1}
          >
            <Box>
              <Typography id={resolvedHeadingId} variant="h4" component="h1">
                {title}
              </Typography>
              {description ? (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {description}
                </Typography>
              ) : null}
            </Box>
            {actions ? <Stack direction="row" spacing={1}>{actions}</Stack> : null}
          </Stack>
          {children}
        </Stack>
      </Paper>
    </Stack>
  );
}
