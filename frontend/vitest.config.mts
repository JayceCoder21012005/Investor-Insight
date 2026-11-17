import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, ".") } },
  test: {
    environment: "jsdom",
    // The default worker pools fail to initialise on Node 26 ("Cannot read properties of undefined (reading 'config')").
    pool: "vmThreads",
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["node_modules", ".next"],
  },
});
