import { test, expect } from "@playwright/test";
import fs from "node:fs/promises";

test("saved geometry evidence exports actual results and survives refresh failure", async ({
  page,
  request,
}) => {
  const response = await request.post("/api/inference/sample", {
    data: { sample: "flange", model: "surface-rf-v1" },
  });
  expect(response.ok()).toBeTruthy();
  const historyResponse = await request.get("/api/drift?limit=100");
  const history = await historyResponse.json();
  const observation = history.observations[0];
  expect(observation.features.length).toBeGreaterThan(0);
  await page.goto("/#Observability");
  const panel = page.getByRole("region", {
    name: "Geometry screening history",
  });
  await panel.getByLabel("Inspect request").selectOption(observation.id);
  const downloadPromise = page.waitForEvent("download");
  await panel.getByRole("button", { name: /Export/ }).click();
  const download = await downloadPromise;
  expect(
    JSON.parse(await fs.readFile((await download.path())!, "utf8")),
  ).toEqual(observation);
  await page.route("**/api/drift?limit=100", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page.getByRole("button", { name: "Refresh data", exact: true }).click();
  await expect(panel.getByRole("status")).toContainText("may be stale");
  await expect(panel.getByLabel("Inspect request")).toHaveValue(observation.id);
  await page.unroute("**/api/drift?limit=100");
  await panel.getByRole("button", { name: "Retry history" }).click();
  await expect(panel.getByText(/may be stale/)).toHaveCount(0);
  await panel.screenshot({ path: "artifacts/history-drift-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  await panel.screenshot({ path: "artifacts/history-drift-mobile.png" });
});

test("registry displays genuine candidate packages and completed lineage", async ({
  page,
  request,
}) => {
  const response = await request.get("/api/registry/candidate-jobs?limit=20");
  const { jobs } = await response.json();
  const job = jobs.find(
    (row: { status: string }) => row.status === "succeeded",
  );
  expect(
    job,
    "Prepare an actual isolated candidate before browser tests",
  ).toBeTruthy();
  await page.goto("/#Model%20Registry");
  const panel = page.getByRole("region", {
    name: "Training execution history",
  });
  await panel
    .getByRole("button", { name: new RegExp(job.id.slice(0, 12)) })
    .click();
  await expect(
    panel.getByText(job.candidate.package_id, { exact: true }),
  ).toBeVisible();
  await panel.screenshot({ path: "artifacts/history-registry-desktop.png" });
  await panel
    .getByRole("button", { name: "Completed runs", exact: true })
    .click();
  const runs = await (await request.get("/api/registry/runs?limit=20")).json();
  await expect(panel.getByText(runs.runs[0].id, { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  await panel.screenshot({ path: "artifacts/history-registry-mobile.png" });
  await panel
    .getByRole("button", { name: "Initialization failures", exact: true })
    .click();
  await expect(
    panel.getByText("No handled initialization failures recorded", {
      exact: true,
    }),
  ).toBeVisible();
});

test("history has honest empty, loading and unavailable states", async ({
  page,
}) => {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/drift?limit=100", async (route) => {
    await pending;
    await route.fulfill({ json: { observations: [] } });
  });
  await page.goto("/#Observability");
  const panel = page.getByRole("region", {
    name: "Geometry screening history",
  });
  await expect(panel.getByText("Loading retained geometry…")).toBeVisible();
  release();
  await expect(
    panel.getByText("No geometry evidence recorded", { exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByText("Below screening threshold", { exact: true }),
  ).toHaveCount(0);
  await page.unroute("**/api/drift?limit=100");
  await page.route("**/api/drift?limit=100", (route) =>
    route.fulfill({ status: 503, body: "unavailable" }),
  );
  await page.getByRole("button", { name: "Refresh data", exact: true }).click();
  await expect(panel.getByRole("status")).toContainText("HTTP 503");
  await expect(
    panel.getByRole("button", { name: "Retry history" }),
  ).toBeVisible();
});

test("operations displays release authorization audit journal records", async ({
  page,
}) => {
  const mockRelease = {
    origin: "Actual append-only release authorization audit journal",
    releases: [
      {
        id: "rel_browser_qa_test",
        at: 1729524000.0,
        operator: "qa-operator@shapeops.internal",
        candidate_id: "surface-et-v2",
        package_id:
          "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        gates: {
          macro_f1: true,
          latency_ms: true,
          security: true,
          dataset_hash: true,
        },
        status: "approved",
        rationale: "Automated browser test release evaluation passes all gates",
      },
    ],
  };

  await page.route("**/api/operations/releases?limit=20", (route) =>
    route.fulfill({ json: mockRelease }),
  );

  await page.goto("/#Operations");
  const panel = page.getByRole("region", {
    name: "Release authorization audit journal",
  });
  await expect(panel).toBeVisible();
  await expect(panel.getByText("Decision: Approved")).toBeVisible();
  await expect(
    panel.getByText("qa-operator@shapeops.internal", { exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByText("Automated browser test release evaluation passes all gates"),
  ).toBeVisible();
  await expect(panel.getByText("macro f1")).toBeVisible();

  // Test export
  const downloadPromise = page.waitForEvent("download");
  await panel.getByRole("button", { name: "Export decision" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(
    "shapeops-release-rel_browser_qa_t.json",
  );

  // Mobile viewport check
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
});
