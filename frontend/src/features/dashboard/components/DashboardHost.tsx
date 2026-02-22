import { Alert, Box, Paper, Stack, Typography } from "@mui/material";
import { Component, type ErrorInfo, type ReactNode } from "react";

import type { DashboardCardAvailability, DashboardSummary } from "../../../shared/types/contracts";

type DashboardHostProps = {
  summary: DashboardSummary | undefined;
  isLoading: boolean;
  isError: boolean;
};

type DashboardCardViewProps = {
  card: DashboardCardAvailability;
};

type DashboardCardRegistration = {
  id: string;
  title: string;
  mount: (props: DashboardCardViewProps) => ReactNode;
  source: "builtin" | "plugin";
};

function SavedFollowupCard({ card }: DashboardCardViewProps) {
  return (
    <Stack spacing={0.7}>
      <Typography variant="h6" component="h2">
        {card.title}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Card host is ready. Saved follow-up data wiring is planned in the command-center data slice.
      </Typography>
    </Stack>
  );
}

function createDashboardCardRegistry(
  registrations: DashboardCardRegistration[]
): Record<string, DashboardCardRegistration> {
  const byId: Record<string, DashboardCardRegistration> = {};
  for (const registration of registrations) {
    if (byId[registration.id]) {
      continue;
    }
    byId[registration.id] = registration;
  }
  return byId;
}

const dashboardCardRegistry = createDashboardCardRegistry([
  {
    id: "saved_followup",
    title: "Saved follow-up",
    mount: SavedFollowupCard,
    source: "builtin",
  },
]);

type DashboardCardErrorBoundaryProps = {
  cardId: string;
  children: ReactNode;
};

type DashboardCardErrorBoundaryState = {
  hasError: boolean;
};

class DashboardCardErrorBoundary extends Component<DashboardCardErrorBoundaryProps, DashboardCardErrorBoundaryState> {
  public constructor(props: DashboardCardErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  public static getDerivedStateFromError(): DashboardCardErrorBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("dashboard.card.render.error", {
      card_id: this.props.cardId,
      error,
      component_stack: errorInfo.componentStack,
    });
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      return <Alert severity="error">Card unavailable</Alert>;
    }
    return this.props.children;
  }
}

function CardFrame({ children }: { children: ReactNode }) {
  return (
    <Paper className="dashboard-card" elevation={0}>
      {children}
    </Paper>
  );
}

function AvailabilityFallback({ card }: { card: DashboardCardAvailability }) {
  const statusTone = card.status === "degraded" ? "warning" : "info";
  return (
    <Stack spacing={0.65}>
      <Typography variant="h6" component="h2">
        {card.title}
      </Typography>
      <Alert severity={statusTone}>
        {card.reason ?? (card.status === "degraded" ? "Temporarily degraded." : "Currently unavailable.")}
      </Alert>
      {card.dependency_spec ? (
        <Typography variant="caption" color="text.secondary">
          Dependency: {card.dependency_spec}
        </Typography>
      ) : null}
    </Stack>
  );
}

function ReadyCardHost({ card }: { card: DashboardCardAvailability }) {
  const registration = dashboardCardRegistry[card.id];
  if (!registration) {
    return (
      <Stack spacing={0.65}>
        <Typography variant="h6" component="h2">
          {card.title}
        </Typography>
        <Alert severity="warning">Card host is registered but no frontend card implementation is mounted.</Alert>
      </Stack>
    );
  }
  const CardMount = registration.mount;
  return (
    <DashboardCardErrorBoundary cardId={card.id}>
      <CardMount card={card} />
    </DashboardCardErrorBoundary>
  );
}

export function DashboardHost({ summary, isLoading, isError }: DashboardHostProps) {
  if (isLoading) {
    return <Typography color="text.secondary">Loading dashboard…</Typography>;
  }
  if (isError) {
    return <Alert severity="error">Failed to load dashboard summary.</Alert>;
  }

  const cards = summary?.cards ?? [];
  if (cards.length === 0) {
    return <Alert severity="info">No dashboard cards are available.</Alert>;
  }

  return (
    <Box className="dashboard-shell">
      <Stack className="dashboard-shell__header" spacing={0.35}>
        <Typography variant="h5" component="h1">
          Dashboard
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Command-center shell is active with card availability contracts.
        </Typography>
      </Stack>
      <Box className="dashboard-grid">
        {cards.map((card) => (
          <CardFrame key={card.id}>
            {card.status === "ready" ? <ReadyCardHost card={card} /> : <AvailabilityFallback card={card} />}
          </CardFrame>
        ))}
      </Box>
    </Box>
  );
}
