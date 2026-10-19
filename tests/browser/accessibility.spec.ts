import { test, expect } from "@playwright/test";
import fs from "node:fs";
import AxeBuilder from "@axe-core/playwright";
test("accessible dark and light workspace screens", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByText("19 faces · mm")).toBeVisible();
  const findings = [];
  for (const theme of ["dark", "light"]) {
    if (theme === "light")
      await page
        .getByRole("button", { name: "Light appearance", exact: true })
        .click();
    for (const screen of [
      "Overview",
      "Inference Studio",
      "Model Registry",
      "Observability",
      "Operations",
      "Documentation",
    ]) {
      await page.goto("/#" + encodeURIComponent(screen));
      await expect(
        page.getByRole("heading", {
          name: screen === "Overview" ? "Workspace overview" : screen,
          exact: true,
        }),
      ).toBeVisible();
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      findings.push({
        theme,
        screen,
        violations: result.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          description: v.description,
          nodes: v.nodes.map((n) => ({
            target: n.target,
            summary: n.failureSummary,
          })),
        })),
      });
    }
  }
  fs.writeFileSync(
    "artifacts/accessibility-audit.json",
    JSON.stringify(findings, null, 2),
  );
  await test
    .info()
    .attach("accessibility-audit", {
      body: JSON.stringify(findings, null, 2),
      contentType: "application/json",
    });
  expect(
    findings.reduce((n, f) => n + f.violations.length, 0),
    "See artifacts/accessibility-audit.json",
  ).toBe(0);
});
