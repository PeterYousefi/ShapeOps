import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/browser",
  timeout: 60000,
  expect: { timeout: 15000 },
  workers: 1,
  use: {
    baseURL: process.env.SHAPEOPS_TEST_BASE_URL || "http://127.0.0.1:5173",
    headless: true,
    reducedMotion: "reduce",
    viewport: { width: 1440, height: 1050 },
    launchOptions: {
      args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-webgl"],
    },
  },
});
