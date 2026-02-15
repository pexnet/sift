import { z } from "zod";

import type { AuthUser } from "../../shared/types/contracts";

const authUserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  display_name: z.string(),
  is_active: z.boolean(),
  is_admin: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export function parseAuthUser(payload: unknown): AuthUser {
  return authUserSchema.parse(payload) as AuthUser;
}
