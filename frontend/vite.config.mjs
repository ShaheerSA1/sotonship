import { defineConfig } from "vite";

export default defineConfig({
  server: {
    forwardConsole: { unhandledErrors: true, logLevels: ["error", "warn", "debug"] },
  },
});
