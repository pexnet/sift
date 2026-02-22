import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import { Component, type ErrorInfo, type ReactNode } from "react";

import type { PluginArea } from "../../../shared/types/contracts";
import { createPluginAreaRegistry } from "./registry";

type PluginAreaHostProps = {
  area: PluginArea;
};

type PluginAreaViewProps = {
  area: PluginArea;
};

function DiscoverFeedsAreaView({ area }: PluginAreaViewProps) {
  return (
    <Box className="workspace-plugin-area">
      <Stack direction="row" spacing={1} alignItems="center" className="workspace-plugin-area__header">
        <SearchRoundedIcon fontSize="small" />
        <Typography variant="h5" component="h1">
          {area.title}
        </Typography>
      </Stack>
      <Typography variant="body2" color="text.secondary" className="workspace-plugin-area__description">
        Plugin host baseline is active. Discovery stream workflows can now mount into this workspace area.
      </Typography>
      <Button variant="outlined" size="small">
        Discovery controls coming next
      </Button>
    </Box>
  );
}

const pluginAreaRegistry = createPluginAreaRegistry([
  {
    id: "discover_feeds",
    title: "Discover feeds",
    mount: DiscoverFeedsAreaView,
    capabilities: {
      supportsBadge: false,
    },
  },
]);

type PluginAreaErrorBoundaryProps = {
  pluginId: string;
  children: ReactNode;
};

type PluginAreaErrorBoundaryState = {
  hasError: boolean;
};

class PluginAreaErrorBoundary extends Component<
  PluginAreaErrorBoundaryProps,
  PluginAreaErrorBoundaryState
> {
  public constructor(props: PluginAreaErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  public static getDerivedStateFromError(): PluginAreaErrorBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("plugin.ui.render.error", {
      plugin_id: this.props.pluginId,
      error,
      component_stack: errorInfo.componentStack,
    });
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      return <Alert severity="error">Plugin unavailable</Alert>;
    }
    return this.props.children;
  }
}

function PluginUnavailable({ areaTitle }: { areaTitle: string }) {
  return (
    <Alert severity="warning">
      Plugin area &quot;{areaTitle}&quot; is enabled but no frontend registration is available.
    </Alert>
  );
}

export function PluginAreaHost({ area }: PluginAreaHostProps) {
  const registration = pluginAreaRegistry.byId[area.id];
  if (!registration) {
    return <PluginUnavailable areaTitle={area.title} />;
  }
  const AreaComponent = registration.mount;
  return (
    <PluginAreaErrorBoundary pluginId={area.id}>
      <AreaComponent area={area} />
    </PluginAreaErrorBoundary>
  );
}
