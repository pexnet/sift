import { z } from "zod";

import type { NavigationResponse } from "../../shared/types/contracts";

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

export type NavigationSystemItem = {
  key: "all" | "fresh" | "saved" | "archived" | "recent";
  title: string;
  unread_count: number;
  kind: "system";
  scope_type: "system";
  scope_id: string;
};

export type NavigationFeedItem = {
  kind: "feed";
  id: string;
  title: string;
  unread_count: number;
  folder_id: string | null;
  folder_name: string;
  scope_type: "feed";
  scope_id: string;
};

export type NavigationFolderItem = {
  id: string | null;
  name: string;
  unread_count: number;
  kind: "folder";
  scope_type: "folder";
  scope_id: string;
  is_unfiled: boolean;
  feeds: NavigationFeedItem[];
};

export type NavigationStreamItem = {
  id: string;
  name: string;
  unread_count: number;
  kind: "stream";
  scope_type: "stream";
  scope_id: string;
};

export type NavigationSection =
  | {
      id: "systems";
      title: "System";
      items: NavigationSystemItem[];
    }
  | {
      id: "monitoring";
      title: "Monitoring feeds";
      items: NavigationStreamItem[];
    }
  | {
      id: "folders";
      title: "Folders";
      items: NavigationFolderItem[];
    }

export type NavigationHierarchy = {
  sections: NavigationSection[];
  systems: NavigationSystemItem[];
  folders: NavigationFolderItem[];
  streams: NavigationStreamItem[];
  feeds: NavigationFeedItem[];
};

export function parseNavigationResponse(payload: unknown): NavigationResponse {
  return navigationTreeSchema.parse(payload) as NavigationResponse;
}

export function toNavigationHierarchy(tree: NavigationResponse): NavigationHierarchy {
  const systems: NavigationSystemItem[] = tree.systems.map((systemNode) => ({
    ...systemNode,
    kind: "system",
    scope_type: "system",
    scope_id: systemNode.key,
  }));

  const folders: NavigationFolderItem[] = tree.folders.map((folderNode) => {
    const isUnfiled = folderNode.id === null;
    const folderName = isUnfiled ? "Unfiled" : folderNode.name;
    const feeds: NavigationFeedItem[] = (folderNode.feeds ?? []).map((feedNode) => ({
      kind: "feed",
      id: feedNode.id,
      title: feedNode.title,
      unread_count: feedNode.unread_count,
      folder_id: folderNode.id,
      folder_name: folderName,
      scope_type: "feed",
      scope_id: feedNode.id,
    }));

    return {
      ...folderNode,
      kind: "folder",
      name: folderName,
      scope_type: "folder",
      scope_id: folderNode.id ?? "",
      is_unfiled: isUnfiled,
      feeds,
    };
  });

  const streams: NavigationStreamItem[] = tree.streams.map((streamNode) => ({
    ...streamNode,
    kind: "stream",
    scope_type: "stream",
    scope_id: streamNode.id,
  }));

  const feeds = folders.flatMap((folderNode) => folderNode.feeds);

  return {
    sections: [
      { id: "systems", title: "System", items: systems },
      { id: "monitoring", title: "Monitoring feeds", items: streams },
      { id: "folders", title: "Folders", items: folders },
    ],
    systems,
    folders,
    streams,
    feeds,
  };
}

export function getScopeLabel(
  hierarchy: NavigationHierarchy,
  scopeType: "system" | "folder" | "feed" | "stream",
  scopeId: string,
  state: string
): string {
  if (scopeType === "system") {
    const systemNode = hierarchy.systems.find((item) => item.scope_id === state);
    return systemNode?.title ?? "All articles";
  }
  if (scopeType === "folder") {
    const folderNode = hierarchy.folders.find((item) => item.scope_id === scopeId);
    return folderNode?.name ?? "Folder";
  }
  if (scopeType === "feed") {
    const feedNode = hierarchy.feeds.find((item) => item.scope_id === scopeId);
    return feedNode?.title ?? "Feed";
  }
  const streamNode = hierarchy.streams.find((item) => item.scope_id === scopeId);
  return streamNode?.name ?? "Stream";
}
