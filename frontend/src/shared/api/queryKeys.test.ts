import { describe, expect, it } from "vitest";

import { queryKeys } from "./queryKeys";

describe("queryKeys", () => {
  it("builds stable auth key", () => {
    expect(queryKeys.auth.me()).toEqual(["auth", "me"]);
  });

  it("builds article key with search dimensions", () => {
    expect(
      queryKeys.articles({
        scope_type: "system",
        scope_id: "",
        state: "all",
        sort: "newest",
        q: "react",
        article_id: "",
      })
    ).toEqual(["articles", "system", "", "all", "newest", "react"]);
  });
});
