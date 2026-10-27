const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const baseURL = process.env.FRESHERFLOW_BASE_URL || "http://127.0.0.1:5000";
const publicRoutes = ["/", "/login", "/register", "/jobs"];

test.use({ baseURL });

test("public landing page exposes a working skip link", async ({ page }) => {
  await page.goto("/");
  const skipLink = page.getByRole("link", { name: /skip to main content/i });

  await expect(skipLink).toHaveAttribute("href", "#main-content");
  await page.keyboard.press("Tab");
  await expect(skipLink).toBeFocused();
  await expect(page.locator("#main-content")).toHaveCount(1);
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("public entry routes load successfully", async ({ page }) => {
  for (const route of publicRoutes) {
    const response = await page.goto(route);
    expect(response, `No response for ${route}`).not.toBeNull();
    expect(response.status(), `Unexpected status for ${route}`).toBe(200);
    await expect(page.locator("body")).toBeVisible();
  }
});

test("landing page fits a narrow mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
  }));

  expect(
    dimensions.document,
    `Unexpected horizontal overflow: document=${dimensions.document}px, viewport=${dimensions.viewport}px`,
  ).toBeLessThanOrEqual(dimensions.viewport + 1);
});

for (const route of publicRoutes) {
  test(`axe accessibility scan: ${route}`, async ({ page }) => {
    await page.goto(route);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const serious = results.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );

    if (results.violations.length) {
      console.log(
        JSON.stringify(
          {
            route,
            totalViolations: results.violations.length,
            seriousOrCritical: serious.length,
            violations: results.violations.map((violation) => ({
              id: violation.id,
              impact: violation.impact,
              description: violation.help,
              nodes: violation.nodes.length,
            })),
          },
          null,
          2,
        ),
      );
    }

    expect(
      serious,
      `Serious/critical accessibility violations on ${route}: ${serious.map((item) => item.id).join(", ")}`,
    ).toEqual([]);
  });
}
