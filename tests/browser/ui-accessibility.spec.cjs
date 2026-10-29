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

<<<<<<< HEAD
=======
test("landing typography stays within the viewport at common responsive widths", async ({ page }) => {
  for (const width of [320, 390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const layout = await page.evaluate(() => {
      const viewport = document.documentElement.clientWidth;
      const documentWidth = document.documentElement.scrollWidth;
      const heading = document.querySelector(".hero-copy h1");
      const headingRect = heading?.getBoundingClientRect();
      const sectionHeadings = [...document.querySelectorAll(
        ".process-head h2, .principles-intro h2, .home-cta h2"
      )].filter((element) => element.getClientRects().length > 0);
      return {
        viewport,
        documentWidth,
        headingVisible: Boolean(heading && headingRect && headingRect.width > 0),
        headingLeft: headingRect?.left ?? -1,
        headingRight: headingRect?.right ?? viewport + 1,
        sectionHeadingsVisible: sectionHeadings.length >= 2,
      };
    });

    expect(
      layout.documentWidth,
      `Horizontal overflow at ${width}px: document=${layout.documentWidth}px`,
    ).toBeLessThanOrEqual(layout.viewport + 1);
    expect(layout.headingVisible, `Hero heading missing at ${width}px`).toBe(true);
    expect(layout.headingLeft, `Hero heading starts outside viewport at ${width}px`).toBeGreaterThanOrEqual(0);
    expect(layout.headingRight, `Hero heading extends outside viewport at ${width}px`).toBeLessThanOrEqual(width + 1);
    expect(layout.sectionHeadingsVisible, `Section headings missing at ${width}px`).toBe(true);
  }
});

test("landing page increases heading and body text for the large-text preference", async ({ page }) => {
  await page.goto("/");
  const normal = await page.locator(".hero-copy h1").evaluate((element) => ({
    heading: parseFloat(getComputedStyle(element).fontSize),
    body: parseFloat(getComputedStyle(document.querySelector(".hero-copy p")).fontSize),
  }));

  await page.locator("body").evaluate((body) => body.setAttribute("data-font-scale", "large"));
  const large = await page.locator(".hero-copy h1").evaluate((element) => ({
    heading: parseFloat(getComputedStyle(element).fontSize),
    body: parseFloat(getComputedStyle(document.querySelector(".hero-copy p")).fontSize),
  }));

  expect(large.heading).toBeGreaterThan(normal.heading);
  expect(large.body).toBeGreaterThan(normal.body);
});

>>>>>>> 534ff53e5c1855bf680fb6ffb921ed9735e7c0be
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


test("landing page keeps serious and critical accessibility checks clear in dark theme", async ({ page }) => {
  await page.goto("/");
  await page.locator("body").evaluate((body) => body.setAttribute("data-theme", "dark"));
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );

  expect(
    serious,
    `Serious/critical dark-theme accessibility violations: ${serious.map((item) => item.id).join(", ")}`,
  ).toEqual([]);
});
