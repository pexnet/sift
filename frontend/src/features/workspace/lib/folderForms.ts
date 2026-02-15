import { z } from "zod";

import type { FeedFolderAssignmentRequest, FeedFolderCreateRequest, FeedFolderUpdateRequest } from "../../../shared/types/contracts";

const folderNameSchema = z.string().trim().min(1, "Folder name is required.").max(255, "Folder name is too long.");

export function toCreateFolderRequest(name: string): FeedFolderCreateRequest {
  return {
    name: folderNameSchema.parse(name),
    description: null,
    sort_order: 100,
  };
}

export function toUpdateFolderRequest(name: string): FeedFolderUpdateRequest {
  return {
    name: folderNameSchema.parse(name),
  };
}

export function toFeedFolderAssignmentRequest(folderId: string | null): FeedFolderAssignmentRequest {
  return {
    folder_id: folderId,
  };
}
