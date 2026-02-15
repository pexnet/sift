import { Badge, Box, ButtonBase, Stack, Tooltip, Typography } from "@mui/material";
import type { ReactNode } from "react";

type WorkspaceRailAction = {
  id: string;
  label: string;
  icon: ReactNode;
  active?: boolean;
  badge?: number;
  onClick?: () => void;
};

type WorkspaceRailProps = {
  actions: WorkspaceRailAction[];
};

export function WorkspaceRail({ actions }: WorkspaceRailProps) {
  return (
    <Box className="workspace-rail" component="aside">
      <Box className="workspace-rail__logo" aria-hidden="true">
        S
      </Box>
      <Stack spacing={1.5}>
        {actions.map((action) => (
          <Tooltip key={action.id} title={action.label} placement="right">
            <ButtonBase
              className={action.active ? "workspace-rail__item workspace-rail__item--active" : "workspace-rail__item"}
              onClick={action.onClick}
              aria-label={action.label}
            >
              <Badge badgeContent={action.badge} color="primary" max={999}>
                <span className="workspace-rail__glyph" aria-hidden="true">{action.icon}</span>
              </Badge>
              <Typography variant="caption" className="workspace-rail__label">
                {action.label}
              </Typography>
            </ButtonBase>
          </Tooltip>
        ))}
      </Stack>
    </Box>
  );
}
