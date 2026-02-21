import { Box, Paper, Stack, Typography } from "@mui/material";
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

export function SettingsLayout({
  activeSection: _activeSection,
  title,
  description,
  actions,
  children,
  headingId,
  maxWidth = 1200,
}: SettingsLayoutProps) {
  const resolvedHeadingId = headingId ?? "settings-page-heading";
  void _activeSection;

  return (
    <Stack sx={{ maxWidth, mx: "auto", width: "100%" }}>
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
