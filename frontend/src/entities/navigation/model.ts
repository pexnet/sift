import { z } from "zod";

import type {
  NavigationFolderNode,
  NavigationResponse,
  NavigationStreamNode,
  NavigationSystemNode,
} from "../../shared/types/contracts";

const navigationSystemSchema = z.object({
  key: z.enum(["all", "fresh", "saved", "archived", "recent"]),
  title: z.string(),
  unread_count: z.number(),
});

const navigationFeedSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  unread_count: z.number(),
});

const navigationFolderSchema = z.object({
  id: z.string().uuid().nullable(),
  name: z.string(),
  unread_count: z.number(),
  feeds: z.array(navigationFeedSchema),
});

const navigationStreamSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  unread_count: z.number(),
});

const navigationTreeSchema = z.object({
  systems: z.array(navigationSystemSchema),
  folders: z.array(navigationFolderSchema),
  streams: z.array(navigationStreamSchema),
});

export type NavigationNode =
  | (NavigationSystemNode & { scope_type: "system"; scope_id: string })
  | (NavigationFolderNode & { scope_type: "folder"; scope_id: string })
  | (NavigationStreamNode & { scope_type: "stream"; scope_id: string });

export function parseNavigationResponse(payload: unknown): NavigationResponse {
  return navigationTreeSchema.parse(payload) as NavigationResponse;
}

export function flattenNavigation(tree: NavigationResponse): NavigationNode[] {
  const systems: NavigationNode[] = tree.systems.map((systemNode) => ({
    ...systemNode,
    scope_type: "system",
    scope_id: systemNode.key,
  }));

  const folders: NavigationNode[] = tree.folders.map((folderNode) => ({
    ...folderNode,
    scope_type: "folder",
    scope_id: folderNode.id ?? "",
  }));

  const streams: NavigationNode[] = tree.streams.map((streamNode) => ({
    ...streamNode,
    scope_type: "stream",
    scope_id: streamNode.id,
  }));

  return [...systems, ...folders, ...streams];
}
