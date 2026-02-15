import { describe, expect, it } from "vitest";

import { validateEmail, validatePassword } from "./validation";

describe("auth validation", () => {
  it("validates email format", () => {
    expect(validateEmail("")).toBe("Email is required.");
    expect(validateEmail("bad-email")).toBe("Email is invalid.");
    expect(validateEmail("dev@sift.local")).toBeNull();
  });

  it("validates password length", () => {
    expect(validatePassword("short")).toBe("Password must be at least 8 characters.");
    expect(validatePassword("long-enough")).toBeNull();
  });
});
