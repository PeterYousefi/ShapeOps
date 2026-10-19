import { test, expect } from "@playwright/test";
import fs from "node:fs";
test("desktop complete engineering walkthrough", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.getByText("Local runtime online")).toBeVisible();
  await expect(page.getByText("19 faces · mm")).toBeVisible();
  await page.screenshot({
    path: "artifacts/overview-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Open studio", exact: false }).click();
  await expect(
    page.getByRole("heading", { name: "Inference Studio", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Face 001", exact: true }).click();
  await expect(page.getByText("SELECTED FACE", { exact: true })).toBeVisible();
  await expect(page.getByText("face:0", { exact: true })).toBeVisible();
  await page
    .locator(".studio-canvas-panel canvas")
    .click({ position: { x: 300, y: 230 } });
  await expect(page.getByText("SELECTED FACE", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await page.getByRole("button", { name: "Reset camera", exact: true }).click();
  await page.getByLabel("Compare", { exact: true }).check();
  await page
    .getByRole("button", { name: "Run inference", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Run inference", exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByRole("term").filter({ hasText: "Disagreements" }),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/studio-desktop.png",
    fullPage: true,
  });
  await page.getByLabel("INPUT", { exact: true }).selectOption("flange");
  await page
    .getByRole("button", { name: "Run inference", exact: true })
    .click();
  await expect(page.locator(".studio-canvas-header h2")).toHaveText(
    "Bearing flange",
  );
  const download = await request.get("/api/samples/housing/download");
  fs.writeFileSync("artifacts/test-upload.step", await download.body());
  await page
    .locator("input[type=file]")
    .setInputFiles("artifacts/test-upload.step");
  await expect(page.getByText("Uploaded CAD", { exact: true })).toBeVisible({
    timeout: 45000,
  });
  await page.locator("input[type=file]").setInputFiles({
    name: "invalid.step",
    mimeType: "application/step",
    buffer: Buffer.from("bad STEP"),
  });
  await expect(page.getByRole("alert")).toContainText("ISO 10303-21");
  await expect(page.locator(".studio-canvas-header h2")).toHaveText(
    "test-upload.step",
  );
  await page.getByRole("button", { name: "Dismiss error" }).click();
  await page
    .getByRole("button", { name: "Model Registry", exact: true })
    .click();
  const releases = page.getByRole("button", {
    name: /surface-et-v2.*ExtraTreesClassifier/,
  });
  await releases.click();
  await expect(releases).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".model-card h2")).toHaveText("surface-et-v2");
  await expect(
    page.getByText("No production promotions recorded", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Model card", exact: true })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toContainText("Artifact SHA-256");
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.screenshot({
    path: "artifacts/registry-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Observability", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Request explorer" }),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/observability-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Operations", exact: true }).click();
  await page
    .getByRole("button", { name: "Run isolated incident drill" })
    .click();
  await expect(
    page.getByText("Stable adapter recovery inference").first(),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/operations-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Documentation", exact: true })
    .click();
  await page
    .getByRole("button", { name: "5-minute walkthrough", exact: true })
    .click();
  await expect(
    page.getByText("Five minutes from geometry to operational confidence."),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/documentation-desktop.png",
    fullPage: true,
  });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.screenshot({
    path: "artifacts/light-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Open studio", exact: false }).click();
  await page.screenshot({
    path: "artifacts/studio-light-desktop.png",
    fullPage: true,
  });
  await expect(page.locator("body")).toHaveJSProperty(
    "scrollWidth",
    await page.locator("body").evaluate((e) => e.clientWidth),
  );
  expect(errors).toEqual([]);
});
test("mobile all screens, navigation, viewport and upload controls", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByText("19 faces · mm")).toBeVisible();
  await page.screenshot({
    path: "artifacts/overview-mobile.png",
    fullPage: true,
  });
  for (const name of [
    "Inference Studio",
    "Model Registry",
    "Observability",
    "Operations",
    "Documentation",
  ]) {
    await page
      .getByRole("button", { name: "Open navigation", exact: true })
      .click();
    await page
      .locator("nav")
      .getByRole("button", {
        name,
        exact: true,
      })
      .click();
    await expect(
      page.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    );
    expect(overflow, `overflow on ${name}`).toBe(false);
    if (name === "Inference Studio") {
      await page.getByRole("button", { name: "Face 002", exact: true }).click();
      await expect(page.getByText("face:1", { exact: true })).toBeVisible();
      await page.screenshot({
        path: "artifacts/studio-mobile.png",
        fullPage: true,
      });
    }
    await page.screenshot({
      path: `artifacts/${name.toLowerCase().replaceAll(" ", "-")}-mobile.png`,
      fullPage: true,
    });
  }
});

test("light lab layout persists over an old dark preference and supports a compact rail", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("shapeops-theme", "dark"),
  );
  await page.goto("/#Inference%20Studio");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.getByText("19 faces · mm")).toBeVisible();
  const canvas = await page
    .locator(".studio-canvas-panel canvas")
    .boundingBox();
  expect(canvas!.width).toBeGreaterThan(650);
  expect(canvas!.height).toBeGreaterThanOrEqual(490);
  await page
    .getByRole("button", { name: "Collapse sidebar", exact: true })
    .click();
  await expect(page.locator(".app")).toHaveClass(/sidebar-collapsed/);
  await page
    .getByRole("button", { name: "Model Registry", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Model Registry", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /surface-et-v2.*ExtraTreesClassifier/ })
    .focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".model-card h2")).toHaveText("surface-et-v2");
  await page
    .getByRole("button", { name: "Inference Studio", exact: true })
    .click();
  for (const width of [1024, 768, 600]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      `overflow at ${width}`,
    ).toBe(false);
    await page
      .getByRole("button", { name: "Reset camera", exact: true })
      .click();
  }
  await page
    .getByRole("button", { name: "Open navigation", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Model Registry", exact: true })
    .click();
  await expect(page.locator(".model-card h2")).toBeVisible();
});
