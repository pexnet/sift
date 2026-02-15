import { describe, expect, it } from "vitest";

import { toCreateFolderRequest, toFeedFolderAssignmentRequest, toUpdateFolderRequest } from "./folderForms";

describe("folderForms", () => {
  it("normalizes and validates create payload", () => {
    expect(toCreateFolderRequest("  Security ")).toEqual({
      name: "Security",
      description: null,
      sort_order: 100,
    });
  });

  it("throws on empty names", () => {
    expect(() => toUpdateFolderRequest("   ")).toThrow();
  });

  it("builds feed assignment payload", () => {
    expect(toFeedFolderAssignmentRequest(null)).toEqual({ folder_id: null });
  });
});
