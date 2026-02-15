import { Card, CardContent, Grid, LinearProgress, Typography } from "@mui/material";

import type { DashboardCardModel } from "../lib/dashboard";

type DashboardRowProps = {
  cards: DashboardCardModel[];
};

function DashboardCard({ card }: { card: DashboardCardModel }) {
  return (
    <Card variant="outlined" sx={{ height: "100%", borderRadius: 3 }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">
          {card.title}
        </Typography>
        <Typography variant="h5" sx={{ mb: 0.5 }}>
          {card.value}
        </Typography>
        {card.progress !== undefined ? <LinearProgress value={card.progress} variant="determinate" sx={{ mb: 1 }} /> : null}
        <Typography variant="body2" color="text.secondary">
          {card.hint}
        </Typography>
      </CardContent>
    </Card>
  );
}

export function DashboardRow({ cards }: DashboardRowProps) {
  return (
    <section>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Dashboard
      </Typography>
      <Grid container spacing={1.5} sx={{ mb: 0.5 }}>
        {cards.map((card) => (
          <Grid key={card.id} size={{ xs: 12, sm: card.size === "sm" ? 6 : 12, md: card.size === "lg" ? 6 : 3 }}>
            <DashboardCard card={card} />
          </Grid>
        ))}
      </Grid>
    </section>
  );
}
