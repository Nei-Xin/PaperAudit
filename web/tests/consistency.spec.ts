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

for (const failure of [false, true]) {
  test(`live events replay, reconnect and ${failure ? "failure" : "completion"}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: failure ? 390 : 1440, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const create = await page.request.post("http://127.0.0.1:8001/api/projects", { multipart: {
      privacy_ack: "true", mode: "learn",
      pdf: { name: "events.pdf", mimeType: "application/pdf", buffer: Buffer.concat([
        readFileSync(new URL("./fixtures/frontend-code.pdf", import.meta.url)), Buffer.from(`\n% events-${failure}\n`),
      ]) },
    } });
    const pid = (await create.json()).project.project_id;
    await page.request.post(`http://127.0.0.1:8001/api/projects/${pid}/code`, { multipart: {
      code_zip: { name: "code.zip", mimeType: "application/zip", buffer: readFileSync(new URL("./fixtures/code.zip", import.meta.url)) },
    } });
    const planned = await page.request.post(`http://127.0.0.1:8001/api/projects/${pid}/consistency-jobs`, {
      data: { privacy_ack: true, mode: "plan" },
    });
    const planJob = (await planned.json()).job_id;
    let planId = "";
    await expect.poll(async () => {
      const jobs = await (await page.request.get(`http://127.0.0.1:8001/api/projects/${pid}/consistency-jobs`)).json();
      const job = jobs.find((j: { job_id: string }) => j.job_id === planJob);
      planId = job.plan_id; return job.status;
    }, { timeout: 20_000 }).toBe("SUCCEEDED");
    const execution = await page.request.post(`http://127.0.0.1:8001/api/projects/${pid}/consistency-plans/${planId}/execute`, {
      data: { privacy_ack: true, selected_ids: [], extra_questions: [failure ? "实时验收失败" : "实时验收"] },
    });
    const jobId = (await execution.json()).job_id;
    const eventUrl = `**/consistency-jobs/${jobId}/events`;
    let connections = 0;
    const cursors: string[] = [];
    page.on("response", async response => {
      if (response.url().endsWith(`/consistency-jobs/${jobId}/events`)) {
        const cursor = (await response.allHeaders())["x-test-event-cursor"];
        if (cursor) cursors.push(cursor);
      }
    });
    // First response intentionally disconnects and duplicates a persisted event id.
    // The next request reaches the real streaming route with Last-Event-ID.
    await page.route(eventUrl, async route => {
      const cursor = (await route.request().allHeaders())["last-event-id"];
      ++connections;
      // React StrictMode may abort the first connection before consuming its body.
      if (!cursor && connections <= 2) {
        const event = { event_id: 1, job_id: jobId, kind: "tool_step", created_at: new Date().toISOString(),
          checkpoint_id: "U01", topic: "", tool: "read_file", arguments: {}, outcome: "重复事件验收", ok: true,
          status: "RUNNING", verdicts: [], pending_review: 0 };
        const frame = `id: 1\nevent: audit\ndata: ${JSON.stringify(event)}\n\n`;
        await route.fulfill({ contentType: "text/event-stream", body: `retry: 100\n\n${frame}${frame}` });
      } else await route.continue();
    });
    await page.goto(`/p/${pid}/consistency`);
    const panel = page.getByRole("region", { name: "任务实时进度" });
    await expect(panel.getByText("读取测试文件 L1–2", { exact: false }).first()).toBeVisible();
    await expect.poll(() => cursors).toContain("1");
    const running = await (await page.request.get(`http://127.0.0.1:8001/api/projects/${pid}/consistency-jobs`)).json();
    expect(running.find((j: { job_id: string }) => j.job_id === jobId).status).toBe("RUNNING");
    await expect(panel.locator('[data-checkpoint-id="U01"]')).toHaveCount(1);
    await expect(panel.getByText("查看 2 个步骤", { exact: true })).toBeVisible();
    await panel.screenshot({ path: testInfo.outputPath("live-progress.png") });
    await page.reload();
    await expect(panel.getByText("读取测试文件 L1–2", { exact: false }).first()).toBeVisible();
    await expect(panel.locator('[data-checkpoint-id="U01"]')).toHaveCount(1);
    await expect(panel.getByRole("status")).toHaveText("任务已结束，事件已同步", { timeout: 20_000 });
    if (failure) {
      await expect(panel.getByText("任务失败，未结束的要点没有最终结论。")).toBeVisible();
      await expect(panel.getByText("未完成", { exact: true })).toBeVisible();
    } else {
      await expect(panel.getByText("一致", { exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "3. 核对报告" })).toBeVisible();
    }
    await panel.screenshot({ path: testInfo.outputPath("finished-progress.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    expect(errors).toEqual([]);
    const endedConnections = connections;
    // Closing end events must stop EventSource's automatic reconnection.
    await page.waitForTimeout(1800);
    expect(connections).toBe(endedConnections);
  });
}
