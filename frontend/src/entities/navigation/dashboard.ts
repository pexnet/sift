import { z } from "zod";

import type { DashboardSummary } from "../../shared/types/contracts";

const dashboardCardAvailabilitySchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  status: z.enum(["ready", "unavailable", "degraded"]),
  reason: z.string().nullable().optional(),
  dependency_spec: z.string().nullable().optional(),
});

const dashboardSummarySchema = z.object({
  cards: z.array(dashboardCardAvailabilitySchema),
  last_updated_at: z.string().min(1),
});

export function parseDashboardSummaryResponse(payload: unknown): DashboardSummary {
  return dashboardSummarySchema.parse(payload) as DashboardSummary;
}
