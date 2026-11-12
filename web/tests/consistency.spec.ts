import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

for (const width of [1440, 390]) {
  test(`planning, review, refresh, execution and stale code at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", e => errors.push(e.message));
    const create = await page.request.post("http://127.0.0.1:8001/api/projects", { multipart: {
      privacy_ack: "true", mode: "learn",
      // Project IDs hash PDF bytes; give each scenario its own PDF identity.
      pdf: { name: `consistency-${width}.pdf`, mimeType: "application/pdf", buffer: Buffer.concat([
        readFileSync(new URL("./fixtures/frontend-code.pdf", import.meta.url)), Buffer.from(`\n% consistency-${width}\n`),
      ]) },
    } });
    expect(create.status()).toBe(201);
    const pid = (await create.json()).project.project_id;
    const code = readFileSync(new URL("./fixtures/code.zip", import.meta.url));
    const upload = await page.request.post(`http://127.0.0.1:8001/api/projects/${pid}/code`, { multipart: {
      code_zip: { name: "code.zip", mimeType: "application/zip", buffer: code },
    } });
    expect(upload.status()).toBe(201);
    await page.goto(`/p/${pid}/consistency`);
    await expect(page.locator(".project-topbar")).toBeVisible();
    await expect(page.getByRole("combobox", { name: "规划方式", exact: true })).toHaveValue("one-shot");
    if (width === 390) {
      await page.getByRole("combobox", { name: "规划方式", exact: true }).selectOption("agent");
      await expect(page.getByText(/尚未证明覆盖更好/)).toBeVisible();
    }
    await page.getByRole("checkbox", { name: /^我同意将论文/ }).check();
    const planningRequest = page.waitForRequest(r => r.url().endsWith("/consistency-jobs") && r.method() === "POST");
    await page.getByRole("button", { name: /生成.*规划/ }).click();
    expect((await planningRequest).postDataJSON().planning_strategy).toBe(width === 390 ? "agent" : "one-shot");
    const review = page.getByRole("region", { name: "审阅规划", exact: true });
    await expect(review).toBeVisible();
    await review.getByRole("checkbox", { name: "评估设置", exact: true }).uncheck();
    await review.getByLabel(/补充问题/).fill("学习率如何调整？");
    await page.reload();
    await expect(review.getByRole("checkbox", { name: "评估设置", exact: true })).not.toBeChecked();
    await expect(review.getByLabel(/补充问题/)).toHaveValue("学习率如何调整？");
    await expect(review.getByRole("button", { name: "开始核对 2 项" })).toBeDisabled();
    await review.getByRole("link", { name: /论文第.*页/ }).first().click();
    await expect(page).toHaveURL(/pdfPage=1/);
    await page.goBack();
    await review.getByRole("checkbox", { name: /^我确认/ }).check();
    const request = page.waitForRequest(r => r.url().endsWith("/execute") && r.method() === "POST");
    await review.getByRole("button", { name: "开始核对 2 项" }).click();
    const body = (await request).postDataJSON();
    expect(body.selected_ids).toEqual(["K01"]);
    expect(body.extra_questions).toEqual(["学习率如何调整？"]);
    await expect(page.getByRole("heading", { name: "3. 核对报告" })).toBeVisible();
    await expect(page.getByText("补充问题：学习率如何调整？")).toBeVisible();
    await expect(page.getByText(/1 个未选择/)).toBeVisible();
    await expect(page.getByRole("link", { name: "待核对 1", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "一致 1", exact: true })).toBeVisible();
    await expect(page.getByText("待核对 · 原判定：一致", { exact: true })).toBeVisible();
    await expect(page.getByText("论文为 40，代码为 20，不支持一致判定。", { exact: true })).toBeVisible();
    await expect(page.getByText("证据支持复核通过", { exact: true })).toBeVisible();
    await expect(page.getByText(/相邻表题 · 第 1 页 · fixture-caption：Table 8/).first()).toBeVisible();
    await page.getByText("仓库地图 · 复用已保存地图 · 新增 0 次请求", { exact: true }).click();
    await expect(page.getByText("训练入口和默认配置", { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: "3. 核对报告" })).toBeVisible();
    await expect(page.getByText("仓库地图 · 复用已保存地图 · 新增 0 次请求", { exact: true })).toBeVisible();
    await expect(page.getByText(/相邻表题 · 第 1 页 · fixture-caption：Table 8/).first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await review.screenshot({ path: testInfo.outputPath("planning-review.png") });
    const changed = await page.request.post(`http://127.0.0.1:8001/api/projects/${pid}/code`, { multipart: {
      code_zip: { name: "replacement.zip", mimeType: "application/zip", buffer: code },
    } });
    expect(changed.status()).toBe(201);
    await review.getByRole("checkbox", { name: /^我确认/ }).check();
    await review.getByRole("button", { name: "开始核对 2 项" }).click();
    await expect(review.getByText(/论文或代码已变化/)).toBeVisible();
    expect(errors).toEqual([]);
  });
}
