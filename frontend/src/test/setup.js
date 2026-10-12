import "@testing-library/jest-dom";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// Keep file previews deterministic even when Vitest exposes Node's native URL.
URL.createObjectURL = () => "blob:mock-url";
URL.revokeObjectURL = () => {};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});
