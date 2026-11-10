import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
const fixtures = JSON.parse(readFileSync(new URL("./fixtures/data.json", import.meta.url), "utf8"));
const pdf = fileURLToPath(new URL("./fixtures/paper.pdf", import.meta.url));

test.beforeEach(async ({ page }) => {
  await page.route(/^http:\/\/127\.0\.0\.1:5180\/api\//, async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api\//, "");
    if (route.request().method() !== "GET") throw new Error("Layout tests must not write data");
    if (path.endsWith("/pdf")) return route.fulfill({ path: pdf, contentType: "application/pdf" });
    let data: unknown;
    if (path === "projects") data = fixtures.projects;
    else if (path === "settings") data = { configured: true, model: "test", api_base: "http://localhost", reasoning_effort: "low", retrieval_top_k: 5, judge_batch_size: 4, deep_audit: false };
    else if (path === "storage") data = { name: "test" };
    else if (/projects\/[^/]+$/.test(path)) data = { ...fixtures.projects.find((p: { project_id: string }) => path.endsWith(p.project_id)), page_count: 2, pages: [{ width: 595, height: 842 }, { width: 595, height: 842 }], suggested_pages: [1] };
    else if (path.endsWith("/jobs")) data = { audit: [], learning: [], review: [], revision: [] };
    else if (path.endsWith("/lecture")) data = path.includes("/empty/") ? null : fixtures.lecture;
    else if (path.endsWith("/review")) data = path.includes("/empty/") ? null : fixtures.review;
    else if (path.endsWith("/audits")) data = [fixtures.record];
    else if (path.endsWith("/audits/audit-1")) data = fixtures.audit;
    else if (path.endsWith("/conversations")) data = { active_conversation_id: "c1", conversations: [{ conversation_id: "c1", title: "会话", paper_history: [{ question: "问题", answer: "回答" }], joint_history: [] }] };
    else throw new Error(`Unhandled fixture: ${path}`);
    await route.fulfill({ json: data });
  });
});

async function fits(page: Page) {
  const result = await page.evaluate(() => ({ w: innerWidth, sw: document.documentElement.scrollWidth, h: innerHeight, sh: document.documentElement.scrollHeight }));
  expect(result.sw).toBeLessThanOrEqual(result.w + 1);
  expect(result.sh).toBeLessThanOrEqual(result.h + 1);
}
async function hitTest(page: Page, selector: string) {
  return page.locator(selector).evaluate((node) => {
    const r = node.getBoundingClientRect();
    return node.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
  });
}
for (const [width, height] of [[2560,1440],[1920,1080],[1440,900],[1280,720],[1024,768],[768,900],[390,844],[320,568],[1440,500]]) {
  test(`all page layouts fit ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const path of ["/", "/p/empty/read", "/p/paper/read", "/p/paper/audit/audit-1", "/p/paper/review", "/p/empty/review"]) {
      await page.goto(path);
      await expect(page.getByRole("link", { name: "PaperAudit", exact: true })).toBeVisible();
      if (path !== "/") await expect(page.locator(".project-topbar")).toBeVisible();
      await page.waitForTimeout(120);
      await fits(page);
    }
    expect(errors).toEqual([]);
  });
}

test("review becomes idle and every tab responds to an ordinary click", async ({ page }) => {
  await page.addInitScript(() => {
    const state = window as typeof window & { digestCount: number };
    state.digestCount = 0;
    const original = crypto.subtle.digest.bind(crypto.subtle);
    crypto.subtle.digest = (...args) => { state.digestCount++; return original(...args); };
  });
  await page.goto("/p/paper/review");
  await expect(page.getByRole("heading", { name: "投稿风险" })).toBeVisible();
  await page.waitForTimeout(300);
  const before = await page.evaluate(() => (window as typeof window & { digestCount: number }).digestCount);
  await page.waitForTimeout(600);
  const after = await page.evaluate(() => (window as typeof window & { digestCount: number }).digestCount);
  expect(after - before).toBe(0);
  for (const label of ["维度评分", "问题", "修改稿与导出", "评审意见"]) await page.getByRole("button", { name: label, exact: true }).click({ timeout: 3000 });
  await page.getByRole("button", { name: /定位原文/ }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("project tabs stay clickable when record selector is present", async ({ page }) => {
  for (const width of [1440,1280,1024,768,390,320]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/p/paper/audit/audit-1");
    await expect(page.getByRole("region", { name: "论断详情", exact: true })).toBeVisible();
    expect(await hitTest(page, 'nav[aria-label="项目视图"] a:last-child')).toBe(true);
    await page.getByRole("navigation", { name: "项目视图" }).getByRole("link", { name: /评审/ }).click();
    await expect(page).toHaveURL(/\/review$/);
  }
});

test("mobile drawer closes with Escape and project navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const trigger = page.getByRole("button", { name: "打开项目侧栏" });
  await trigger.click();
  const drawer = page.getByRole("dialog", { name: "论文项目", exact: true });
  await expect(drawer).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await drawer.getByRole("link", { name: /Layout Test Paper/ }).click();
  await expect(drawer).not.toBeVisible();
  await expect(page.locator(".project-topbar")).toBeVisible();
});

test("reader pane switch preserves chapter and citation opens the original", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/p/paper/read");
  await expect(page.locator("canvas.react-pdf__Page__canvas")).toBeVisible();
  await page.getByRole("button", { name: "助手与设置", exact: true }).click();
  await page.getByRole("combobox", { name: "章节", exact: true }).selectOption("1");
  await expect(page.getByRole("button", { name: "发送", exact: true })).toBeInViewport();
  await page.getByRole("button", { name: /Introduction.*↗/ }).click();
  await expect(page.getByRole("region", { name: "论文原文", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "助手与设置", exact: true }).click();
  await expect(page.getByRole("combobox", { name: "章节", exact: true })).toHaveValue("1");
});

test("wide screens split judgment and evidence into separate columns", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/p/paper/audit/audit-1");
  const evidence = page.getByRole("region", { name: "原文依据", exact: true });
  await expect(evidence.locator(".pdf-crop canvas")).toBeVisible();
  const detail = await page.getByRole("region", { name: "论断详情", exact: true }).boundingBox();
  const side = await evidence.boundingBox();
  expect(side!.x).toBeGreaterThan(detail!.x + detail!.width - 1);
  // A lone crop fills the evidence column, also after the column remounts (tab switch).
  const cropHeight = () => evidence.locator(".pdf-crop").first().evaluate((el) => el.getBoundingClientRect().height);
  await page.getByRole("button", { name: "统计与核对", exact: true }).click();
  await page.getByRole("button", { name: "逐条审计", exact: true }).click();
  await expect(evidence.locator(".pdf-crop canvas").first()).toBeVisible();
  await expect.poll(cropHeight).toBeGreaterThan(400);
  // Laptop widths keep three columns (sidebar becomes an icon rail); tablets stack the viewer below.
  await page.setViewportSize({ width: 1366, height: 800 });
  const laptop = await evidence.boundingBox();
  const laptopDetail = await page.getByRole("region", { name: "论断详情", exact: true }).boundingBox();
  expect(laptop!.x).toBeGreaterThan(laptopDetail!.x + laptopDetail!.width - 1);
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.waitForTimeout(300);
  await evidence.scrollIntoViewIfNeeded();
  await expect(evidence).toBeVisible();
  const below = await evidence.boundingBox();
  const above = await page.getByRole("region", { name: "论断详情", exact: true }).boundingBox();
  expect(below!.y).toBeGreaterThanOrEqual(above!.y + above!.height - 1);
});

test("evidence crop is readable inline and the full page opens with zoom", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 500 });
  await page.goto("/p/paper/audit/audit-1");
  const crop = page.locator(".pdf-crop").first();
  await expect(crop.locator("canvas.react-pdf__Page__canvas")).toBeVisible();
  // The crop magnifies the cited lines instead of shrinking the whole page into a side column.
  const scale = await crop.evaluate((el) => (el.querySelector("canvas") as HTMLCanvasElement).getBoundingClientRect().width / 595);
  expect(scale).toBeGreaterThan(1.2);
  await page.getByRole("button", { name: "整页", exact: true }).first().click();
  const modal = page.getByRole("dialog", { name: /^原文 · 第 1 页/ });
  await modal.getByRole("button", { name: "放大", exact: true }).click();
  await expect(modal.getByText("110%", { exact: true })).toBeVisible();
  await expect(modal.getByRole("button", { name: "关闭", exact: true })).toBeInViewport();
  await fits(page);
});

test("mobile claim list, filters and dialog footer remain reachable", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto("/p/paper/audit/audit-1");
  await page.getByRole("button", { name: /论断列表/ }).click();
  await page.getByRole("dialog").getByRole("button", { name: /示例论断 1/ }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByText("筛选", { exact: true }).click();
  await expect(page.getByRole("combobox", { name: /^排序/ })).toBeInViewport();
  await page.getByText("筛选", { exact: true }).click();
  await page.getByRole("button", { name: "审计报告", exact: true }).click();
  const modal = page.getByRole("dialog", { name: "审计一份报告", exact: true });
  await expect(modal.getByRole("button", { name: "取消", exact: true })).toBeInViewport();
  await expect(modal.getByRole("button", { name: "开始审计", exact: true })).toBeInViewport();
  await expect(modal.getByRole("button", { name: "关闭", exact: true })).toBeInViewport();
  await fits(page);
});

test("long uploaded filename wraps inside its card", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const name = "LongPaperFilenameWithoutSpaces".repeat(7) + ".pdf";
  await page.locator('input[accept="application/pdf"]').setInputFiles({ name, mimeType: "application/pdf", buffer: readFileSync(pdf) });
  const title = page.getByTitle(name, { exact: true });
  await expect(title).toBeVisible();
  const box = await title.boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  await fits(page);
});

for (const label of ["NO_SUPPORT_FOUND", "ABSTAIN"]) {
  test(`unselected candidates can be inspected for ${label}`, async ({ page }) => {
    const audit = structuredClone(fixtures.audit);
    const claim = audit.run.audits.find((item: { judgment: { label: string } }) => item.judgment.label === label);
    claim.candidates.push({
      ...claim.candidates[0], evidence_id: "candidate-2", chunk_id: "p2_candidate", page: 2,
      text: "Second candidate with distinct evidence text.",
    });
    await page.route("http://127.0.0.1:5180/api/projects/paper/audits/audit-1", (route) => route.fulfill({ json: audit }));
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/p/paper/audit/audit-1?claim=${claim.claim.claim_id}`);
    const viewer = page.getByRole("region", { name: "原文依据", exact: true });
    const tabs = viewer.getByRole("tablist", { name: "候选原文片段" }).getByRole("tab");
    await tabs.nth(1).click();
    await expect(tabs.nth(1)).toHaveAttribute("aria-selected", "true");
    await expect(viewer.getByText(claim.candidates[1].text, { exact: true })).toBeVisible();
    await expect(viewer.getByText(claim.candidates[0].text, { exact: true })).toHaveCount(0);
    await tabs.nth(0).click();
    await expect(tabs.nth(0)).toHaveAttribute("aria-selected", "true");
    await expect(viewer.getByText(claim.candidates[0].text, { exact: true })).toBeVisible();
  });
}

for (const width of [390, 1440, 1920]) {
  test(`review section links restore their scroll position at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const [tab, heading] of [["issues", "问题清单"], ["dimensions", "维度评分"], ["revisions", "修改稿与导出"]]) {
      await page.goto(`/p/paper/review?tab=${tab}`);
      await expect(page.locator(`#review-${tab}`).getByRole("heading", { name: heading, exact: true })).toBeInViewport();
    }
    await page.reload();
    await expect(page.locator("#review-revisions").getByRole("heading", { name: "修改稿与导出", exact: true })).toBeInViewport();
    const nav = page.getByRole("navigation", { name: "评审视图" });
    await nav.getByRole("button", { name: "评审意见", exact: true }).click();
    await expect(page.getByRole("region", { name: "结论与理由" })).toBeInViewport();
    await nav.getByRole("button", { name: "修改稿与导出", exact: true }).click();
    await expect(page.locator("#review-revisions").getByRole("heading", { name: "修改稿与导出", exact: true })).toBeInViewport();
    await expect(nav.getByRole("button", { name: "修改稿与导出", exact: true })).toHaveAttribute("aria-current", "true");
    await fits(page);
  });
}

test("crossing a review breakpoint keeps the reader's position instead of re-applying the URL section", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 900 });
  await page.goto("/p/paper/review?tab=revisions");
  await expect(page.locator(".review-outline")).toBeVisible();
  await expect(page.locator("#review-revisions").getByRole("heading", { name: "修改稿与导出", exact: true })).toBeInViewport();
  await page.locator(".review-main").evaluate((element) => element.scrollTo({ top: 0 }));
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator(".review-outline")).toHaveCount(0);
  await page.waitForTimeout(300);
  const scrollTop = await page.locator(".review-main").evaluate((element) => element.scrollTop);
  expect(scrollTop).toBeLessThan(40);
  await expect(page.getByRole("region", { name: "结论与理由" })).toBeInViewport();
});

test("desktop dimensions expose confidence, full reasons and every evidence link", async ({ page }) => {
  const review = structuredClone(fixtures.review);
  const dimension = review.report.dimensions[0];
  dimension.rationale = "完整评分理由需要结合实验设计和对照结果核查。".repeat(20);
  dimension.evidence.push({ ...dimension.evidence[0], chunk_id: "p2_dimension", page: 2 });
  await page.route("http://127.0.0.1:5180/api/projects/paper/review", (route) => route.fulfill({ json: review }));
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/p/paper/review?tab=dimensions");
  const scores = page.locator("#review-dimensions");
  await expect(scores.getByText(`置信度 ${dimension.confidence} / 5`, { exact: true })).toBeVisible();
  await scores.getByText("查看完整评分理由", { exact: true }).click();
  const rationale = scores.getByText(dimension.rationale, { exact: true });
  await expect(rationale).toBeVisible();
  expect(await rationale.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
  await expect(scores.getByRole("button", { name: /定位原文/ })).toHaveCount(2);
  await scores.getByRole("button", { name: "定位原文 · 第 2 页", exact: true }).click();
  const modal = page.getByRole("dialog", { name: "原文证据 · 第 2 页", exact: true });
  await expect(modal.locator('canvas')).toBeVisible();
  await modal.getByRole("button", { name: "关闭", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(scores.getByText(`置信度 ${dimension.confidence} / 5`, { exact: true })).toBeVisible();
  await expect(scores.getByRole("button", { name: /定位原文/ })).toHaveCount(2);
  await fits(page);
});


test("lecture overview, all chapters and recommended pages remain usable on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/p/paper/read");
  await page.getByRole("button", { name: "助手与设置", exact: true }).click();
  const pane = page.getByRole("region", { name: "讲解与追问", exact: true });
  await expect(pane.getByRole("region", { name: "阅读导览" })).toBeVisible();
  await expect(pane.getByRole("button", { name: "重新生成详细讲解", exact: true })).toBeDisabled();
  await pane.getByRole("radio", { name: "全部章节", exact: true }).click();
  const titles = fixtures.lecture.sections.map((s: { points: unknown[] }) => s.points.length);
  await expect(pane.locator("ol > li")).toHaveCount(titles.reduce((a: number, b: number) => a + b, 0));
  await pane.getByRole("radio", { name: "本节全部", exact: true }).click();
  await expect(pane.locator("ol > li")).toHaveCount(titles[0]);
  await pane.getByText("推荐阅读页", { exact: true }).click();
  const recommended = fixtures.lecture.suggested_pages[0];
  await pane.getByRole("button", { name: `第 ${recommended} 页`, exact: true }).click();
  await expect(page.getByRole("region", { name: "论文原文", exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: /^页码，共/ })).toHaveValue(String(recommended));
  await fits(page);
});
