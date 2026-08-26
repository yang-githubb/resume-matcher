import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    // These tests cover request and stream parsing, not rendering, so Node's
    // globals (fetch, ReadableStream, TextDecoder) are all they need - no
    // jsdom, and no browser environment to keep in sync.
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
