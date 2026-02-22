import { z } from "zod";

import type { PluginArea } from "../../shared/types/contracts";

const pluginAreaSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  icon: z.string().nullable().optional(),
  order: z.number().int(),
  route_key: z.string().min(1),
});

export function parsePluginAreasResponse(payload: unknown): PluginArea[] {
  return z.array(pluginAreaSchema).parse(payload) as PluginArea[];
}
