import { test, expect } from "@playwright/test";
import * as THREE from "three";
import AxeBuilder from "@axe-core/playwright";
import { fitGeometry } from "../../src/cameraFit";

for (const [name, size] of Object.entries({
  flat: [100, 72, 3],
  shaft: [12, 12, 250],
  tiny: [0.01, 0.02, 0.04],
  large: [10000, 30000, 5000],
})) {
  test(`camera keeps ${name} geometry centered and inside portrait and desktop frusta`, () => {
    const points: THREE.Vector3[] = [];
    for (const x of [-1, 1])
      for (const y of [-1, 1])
        for (const z of [-1, 1])
          points.push(
            new THREE.Vector3(
              (x * size[0]) / 2,
              (y * size[1]) / 2,
              (z * size[2]) / 2,
            ),
          );
    for (const aspect of [0.65, 1, 2.1]) {
      const fit = fitGeometry(
        points,
        new THREE.Vector3(1, -1.25, 1.05),
        34,
        aspect,
      );
      const camera = new THREE.PerspectiveCamera(
        34,
        aspect,
        0.0000001,
        10000000,
      );
      camera.up.set(0, 0, 1);
      camera.position.copy(fit.position);
      camera.lookAt(fit.target);
      camera.updateMatrixWorld();
      const projected = points.map((p) => p.clone().project(camera));
      expect(
        projected.every((p) => Math.abs(p.x) < 0.9 && Math.abs(p.y) < 0.9),
      ).toBe(true);
      expect(
        Math.max(...projected.flatMap((p) => [Math.abs(p.x), Math.abs(p.y)])),
      ).toBeGreaterThan(0.7);
      const box = new THREE.Box3().setFromPoints(projected);
      expect(Math.abs(box.getCenter(new THREE.Vector3()).x)).toBeLessThan(0.12);
      expect(Math.abs(box.getCenter(new THREE.Vector3()).y)).toBeLessThan(0.12);
    }
  });
}

test("Studio real geometry, comparison layers, upload and contextual inspection", async ({
  page,
  request,
}) => {
  await page.goto("/#Inference%20Studio");
  await expect(page.getByText("19 faces · mm")).toBeVisible();
  for (const sample of ["shaft", "housing", "manifold"]) {
    await page.getByLabel("INPUT", { exact: true }).selectOption(sample);
    await page
      .getByLabel("Model version")
      .selectOption(sample === "housing" ? "surface-et-v2" : "surface-rf-v1");
    await page.getByLabel("Compare", { exact: true }).check();
    await page
      .getByRole("button", { name: "Run inference", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Run inference", exact: true }),
    ).toBeEnabled();
    await expect(page.locator(".class-breakdown")).toContainText("faces");
    await page.getByRole("button", { name: "Face 002", exact: true }).click();
    await expect(
      page.getByRole("meter", { name: "Selected face confidence" }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Focus selected face", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Reset camera", exact: true })
      .click();
    await page
      .getByRole("group", { name: "Prediction layer" })
      .getByRole("button")
      .nth(1)
      .click();
    await expect(page.getByLabel("Viewport coloring")).toHaveValue("alternate");
    await page
      .getByRole("group", { name: "Prediction layer" })
      .getByRole("button", { name: /Differences/ })
      .click();
    const changed = page.getByRole("button", {
      name: "Next disagreement",
      exact: false,
    });
    if (await changed.isEnabled()) {
      await changed.click();
      await expect(page.locator(".face-comparison.changed")).toBeVisible();
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `artifacts/studio-refined-${sample}.png`,
      fullPage: true,
    });
  }
  const step = await request.get("/api/samples/flange/download");
  await page.locator("input[type=file]").setInputFiles({
    name: "precision-flange.step",
    mimeType: "application/step",
    buffer: await step.body(),
  });
  await expect(page.locator(".studio-canvas-header h2")).toHaveText(
    "precision-flange.step",
    { timeout: 45000 },
  );
  await page.getByRole("button", { name: "Face 002", exact: true }).click();
  await page.getByText("Class probabilities", { exact: true }).click();
  await expect(page.locator(".class-probabilities")).toContainText("Planar");
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.screenshot({
    path: "artifacts/studio-refined-upload.png",
    fullPage: true,
  });
  await page.locator("input[type=file]").setInputFiles({
    name: "mesh.obj",
    mimeType: "text/plain",
    buffer: Buffer.from("unsupported"),
  });
  await expect(page.getByRole("alert")).toContainText(
    "Unsupported file format",
  );
  await expect(page.locator(".studio-canvas-header h2")).toHaveText(
    "precision-flange.step",
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.screenshot({ path: "artifacts/studio-refined-unsupported.png" });
  await page.getByRole("button", { name: "Dismiss error" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator("body")).toHaveJSProperty("scrollWidth", 390);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "artifacts/studio-refinement-after-mobile.png",
    fullPage: true,
  });
});

test("Studio presents genuine processing and recoverable empty error states", async ({
  page,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/inference/sample", async (route) => {
    const response = await route.fetch();
    await gate;
    await route.fulfill({ response });
  });
  await page.goto("/#Inference%20Studio");
  await expect(page.getByRole("status")).toContainText("Analyzing geometry");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "artifacts/studio-refined-processing.png" });
  release();
  await expect(page.getByText("19 faces · mm")).toBeVisible();
  await page.unroute("**/api/inference/sample");
  await page.route("**/api/inference/sample", (route) =>
    route.abort("connectionfailed"),
  );
  await page.reload();
  await expect(page.getByRole("alert")).toContainText(
    "Analysis could not complete",
  );
  await expect(
    page.getByText("No analysis yet", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Reference screening unavailable", { exact: true }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "artifacts/studio-refined-empty-error.png" });
});
