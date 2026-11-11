import { defineConfig } from "@playwright/test";
export default defineConfig({
  outputDir: "./test-results/reading",
  testDir: "./tests", testMatch: ["reading.spec.ts", "audit.spec.ts", "frontend.spec.ts", "consistency.spec.ts"], workers: 1,
  timeout: 45_000,
  use: {
    baseURL: "http://127.0.0.1:5181", headless: true,
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {},
    screenshot: "only-on-failure", trace: "retain-on-failure",
  },
  webServer: [
    { command: "cd .. && uv run --locked python tests/reading_server.py", url: "http://127.0.0.1:8001/api/projects", reuseExistingServer: false },
    { command: "VITE_READ_ONLY=0 VITE_API_PROXY=http://127.0.0.1:8001 npm run dev -- --port 5181 --strictPort", url: "http://127.0.0.1:5181", reuseExistingServer: false },
  ],
});
