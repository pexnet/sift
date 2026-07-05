import { Alert, Box, Chip, CircularProgress, Link, Paper, Stack, Typography } from "@mui/material";
import { Component, type ErrorInfo, type ReactNode } from "react";

import {
  useDashboardDiscoveryCandidatesQuery,
  useDashboardFeedHealthQuery,
  useDashboardMonitoringSignalsQuery,
  useDashboardPrioritizedQueueQuery,
  useDashboardSavedFollowupQuery,
  useDashboardTrendsQuery,
} from "../api/dashboardHooks";
import type { DashboardCardAvailability, DashboardSummary } from "../../../shared/types/contracts";

type DashboardHostProps = {
  summary: DashboardSummary | undefined;
  isLoading: boolean;
  isError: boolean;
  registryById?: Record<string, DashboardCardRegistration>;
};

type DashboardCardViewProps = {
  card: DashboardCardAvailability;
};

export type DashboardCardRegistration = {
  id: string;
  title: string;
  mount: (props: DashboardCardViewProps) => ReactNode;
  source: "builtin" | "plugin";
};

function CardLoading() {
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <CircularProgress size={16} />
      <Typography variant="body2" color="text.secondary">
        Loading…
      </Typography>
    </Stack>
  );
}

function CardError() {
  return <Alert severity="warning">Failed to load card data.</Alert>;
}

function ScoreChip({ score }: { score: number }) {
  const tone = score >= 60 ? "success" : "default";
  return <Chip label={score.toFixed(0)} size="small" color={tone} />;
}

function PrioritizedQueueCard({ card }: DashboardCardViewProps) {
  const query = useDashboardPrioritizedQueueQuery();
  if (query.isLoading) return <CardLoading />;
  if (query.isError) return <CardError />;
  const data = query.data;
  if (!data || data.items.length === 0) {
    return (
      <Stack spacing={0.7}>
        <Typography variant="h6" component="h2">
          {card.title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No prioritized articles right now.
        </Typography>
      </Stack>
    );
  }
  return (
    <Stack spacing={0.7}>
      <Typography variant="h6" component="h2">
        {card.title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Weights: feed={data.profile.source_weights.feed ?? 40}, stream={data.profile.source_weights.monitoring_stream ?? 60}
      </Typography>
      {data.items.slice(0, 5).map((item) => (
        <Stack key={item.article_id} spacing={0.2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <ScoreChip score={item.priority_score} />
            <Typography variant="body2" noWrap>
              {item.canonical_url ? (
                <Link href={item.canonical_url} target="_blank" rel="noopener" underline="hover">
                  {item.title}
                </Link>
              ) : (
                item.title
              )}
            </Typography>
          </Stack>
          {item.feed_title ? (
            <Typography variant="caption" color="text.secondary">
              {item.feed_title}
            </Typography>
          ) : null}
        </Stack>
      ))}
    </Stack>
  );
}

function FeedHealthCard({ card }: DashboardCardViewProps) {
  const query = useDashboardFeedHealthQuery();
  if (query.isLoading) return <CardLoading />;
  if (query.isError) return <CardError />;
  const data = query.data;
  if (!data) return <CardError />;
  return (
    <Stack spacing={0.7}>
      <Typography variant="h6" component="h2">
        {card.title}
      </Typography>
      <Stack direction="row" spacing={1}>
        {data.stale_feed_count > 0 ? (
          <Chip label={`${data.stale_feed_count} stale`} size="small" color="warning" />
        ) : (
          <Chip label="No stale feeds" size="small" color="success" />
        )}
        {data.error_feed_count > 0 ? (
          <Chip label={`${data.error_feed_count} errors`} size="small" color="error" />
        ) : null}
      </Stack>
      {data.oldest_success_age_hours !== null ? (
        <Typography variant="caption" color="text.secondary">
          Oldest success: {data.oldest_success_age_hours}h ago
        </Typography>
      ) : null}
      {data.queue_lag?.unavailable_reason ? (
        <Typography variant="caption" color="text.secondary">
          {data.queue_lag.unavailable_reason}
        </Typography>
      ) : null}
    </Stack>
  );
}

function SavedFollowupCard({ card }: DashboardCardViewProps) {
  const query = useDashboardSavedFollowupQuery();
  if (query.isLoading) return <CardLoading />;
  if (query.isError) return <CardError />;
  const data = query.data;
  if (!data || data.latest_items.length === 0) {
    return (
      <Stack spacing={0.7}>
        <Typography variant="h6" component="h2">
          {card.title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No saved articles yet.
        </Typography>
      </Stack>
    );
  }
  return (
    <Stack spacing={0.7}>
      <Typography variant="h6" component="h2">
        {card.title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {data.saved_count} saved
      </Typography>
      {data.latest_items.slice(0, 5).map((item) => (
        <Stack key={item.article_id} spacing={0.2}>
          <Typography variant="body2" noWrap>
            {item.canonical_url ? (
              <Link href={item.canonical_url} target="_blank" rel="noopener" underline="hover">
                {item.title}
              </Link>
            ) : (
              item.title
            )}
          </Typography>
          {item.feed_title ? (
            <Typography variant="caption" color="text.secondary">
              {item.feed_title}
            </Typography>
          ) : null}
        </Stack>
      ))}
    </Stack>
  );
}

function MonitoringSignalsCard({ card }: DashboardCardViewProps) {
  const query = useDashboardMonitoringSignalsQuery(24);
  if (query.isLoading) return <CardLoading />;
  if (query.isError) return <CardError />;
  const data = query.data;
  if (!data || data.streams.length === 0) {
    return (
      <Stack spacing={0.7}>
        <Typography variant="h6" component="h2">
          {card.title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No active monitoring streams.
        </Typography>
      </Stack>
    );
  }
  return (
    <Stack spacing={0.7}>
      <Typography variant="h6" component="h2">
        {card.title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Last {data.window_hours}h
      </Typography>
      {data.streams.slice(0, 5).map((stream) => (
        <Stack key={stream.stream_id} spacing={0.2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <ScoreChip score={stream.signal_score} />
            <Typography variant="body2" noWrap>
              {stream.stream_name}
            </Typography>
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {stream.matched_count_window} matches, {stream.unread_count_window} unread
          </Typography>
        </Stack>
      ))}
    </Stack>
  );
}

function DiscoveryCandidatesCard({ card }: DashboardCardViewProps) {
  const query = useDashboardDiscoveryCandidatesQuery();
  if (query.isLoading) return <CardLoading />;
  if (query.isError) return <CardError />;
  const data = query.data;
  if (!data || data.candidates.length === 0) {
    return (
      <Stack spacing={0.7}>
        <Typography variant="h6" component="h2">
          {card.title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {data?.pending_recommendation_count ?? 0} pending recommendations.
        </Typography>
      </Stack>
    );
  }
  return (
    <Stack spacing={0.7}>
      <Typography variant="h6" component="h2">
        {card.title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {data.pending_recommendation_count} pending
      </Typography>
      {data.candidates.slice(0, 5).map((candidate, idx) => (
        <Stack key={candidate.recommendation_id ?? idx} spacing={0.2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <ScoreChip score={candidate.candidate_score} />
            <Typography variant="body2" noWrap>
              {candidate.canonical_url ? (
                <Link href={candidate.canonical_url} target="_blank" rel="noopener" underline="hover">
                  {candidate.title}
                </Link>
              ) : (
                candidate.title
              )}
            </Typography>
          </Stack>
          {candidate.why_candidate[0] ? (
            <Typography variant="caption" color="text.secondary">
              {candidate.why_candidate[0]}
            </Typography>
          ) : null}
        </Stack>
      ))}
    </Stack>
  );
}

function TrendsCard({ card }: DashboardCardViewProps) {
  const query = useDashboardTrendsQuery(24, 14);
  if (query.isLoading) return <CardLoading />;
  if (query.isError) return <CardError />;
  const data = query.data;
  if (!data || data.topics.length === 0) {
    return (
      <Stack spacing={0.7}>
        <Typography variant="h6" component="h2">
          {card.title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No trending topics detected.
        </Typography>
      </Stack>
    );
  }
  return (
    <Stack spacing={0.7}>
      <Typography variant="h6" component="h2">
        {card.title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {data.window_hours}h window vs {data.baseline_days}d baseline
      </Typography>
      {data.topics.slice(0, 8).map((topic) => (
        <Stack key={topic.topic} direction="row" spacing={1} alignItems="center">
          <Chip label={topic.topic} size="small" />
          <Typography variant="caption" color="text.secondary">
            {topic.short_window_count} recent (vs {topic.baseline_count} baseline), {topic.source_diversity_count} sources
          </Typography>
        </Stack>
      ))}
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
  { id: "prioritized_queue", title: "Prioritized queue", mount: PrioritizedQueueCard, source: "builtin" },
  { id: "feed_health", title: "Feed ops health", mount: FeedHealthCard, source: "builtin" },
  { id: "saved_followup", title: "Saved follow-up", mount: SavedFollowupCard, source: "builtin" },
  { id: "monitoring_signals", title: "Monitoring signal", mount: MonitoringSignalsCard, source: "builtin" },
  { id: "trends", title: "Trends", mount: TrendsCard, source: "builtin" },
  { id: "discovery_candidates", title: "Discovery candidates", mount: DiscoveryCandidatesCard, source: "builtin" },
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

function ReadyCardHost({
  card,
  registryById,
}: {
  card: DashboardCardAvailability;
  registryById: Record<string, DashboardCardRegistration>;
}) {
  const registration = registryById[card.id];
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

export function DashboardHost({
  summary,
  isLoading,
  isError,
  registryById = dashboardCardRegistry,
}: DashboardHostProps) {
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
          Command-center with live card data from all six dashboard endpoints.
        </Typography>
      </Stack>
      <Box className="dashboard-grid">
        {cards.map((card) => (
          <CardFrame key={card.id}>
            {card.status === "ready" ? <ReadyCardHost card={card} registryById={registryById} /> : <AvailabilityFallback card={card} />}
          </CardFrame>
        ))}
      </Box>
    </Box>
  );
}