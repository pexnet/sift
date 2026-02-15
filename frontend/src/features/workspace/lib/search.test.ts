import { describe, expect, it } from "vitest";

import { parseWorkspaceSearch } from "../../../entities/article/model";

describe("parseWorkspaceSearch", () => {
  it("applies defaults for missing fields", () => {
    expect(parseWorkspaceSearch({})).toEqual({
      scope_type: "system",
      scope_id: "",
      state: "all",
      sort: "newest",
      q: "",
      article_id: "",
    });
  });

  it("keeps valid values", () => {
    expect(
      parseWorkspaceSearch({
        scope_type: "stream",
        scope_id: "abc",
        state: "saved",
        sort: "unread_first",
        q: "foo",
        article_id: "xyz",
      })
    ).toEqual({
      scope_type: "stream",
      scope_id: "abc",
      state: "saved",
      sort: "unread_first",
      q: "foo",
      article_id: "xyz",
    });
  });
});
