import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
const fixture = (name: string) =>
  fileURLToPath(new URL(`./fixtures/${name}`, import.meta.url));
async function home(page: Page, pdf: string) {
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(fixture(pdf));
  await page.getByRole("checkbox", { name: /我同意/ }).check();
}
async function fits(page: Page) {
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <= innerWidth + 1 &&
        document.documentElement.scrollHeight <= innerHeight + 1,
    ),
  ).toBe(true);
}

test("review retry, human edits, persistent progress, related work and revision", async ({
  page,
}, testInfo) => {
  test.setTimeout(60000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await home(page, "frontend-review.pdf");
  await page.getByRole("radio", { name: "模拟投稿评审", exact: true }).click();
  await page.getByLabel("评审标准", { exact: true }).selectOption("custom");
  await page.getByLabel("可靠性", { exact: true }).fill("60");
  await page.getByRole("button", { name: "开始评审", exact: true }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByText(/评审未完成/)).toBeVisible({ timeout: 15000 });
  await page.reload();
  await page.getByRole("button", { name: "重试评审", exact: true }).click();
  await expect(page.getByRole("heading", { name: "投稿风险" })).toBeVisible({
    timeout: 15000,
  });
  const progress = page.getByRole("checkbox", {
    name: "第 1 步已完成",
    exact: true,
  });
  await page.route(
    "**/review/progress",
    (route) =>
      route.fulfill({
        status: 500,
        json: { error: { message: "测试保存失败" } },
      }),
    { times: 1 },
  );
  await progress.click();
  await expect(page.getByText("测试保存失败", { exact: true })).toBeVisible();
  await expect(progress).not.toBeChecked();
  await progress.check();
  await expect(progress).toBeChecked();
  await expect(progress).toBeEnabled();
  await page.reload();
  await expect(progress).toBeChecked();
  await page.getByRole("button", { name: "问题", exact: true }).click();
  await page
    .getByRole("button", { name: "人工复核", exact: true })
    .first()
    .click();
  const dialog = page.getByRole("dialog", { name: "人工复核问题" });
  await dialog.getByLabel("处理状态", { exact: true }).selectOption("resolved");
  await dialog
    .getByLabel("人工结论", { exact: true })
    .selectOption("confirmed");
  await dialog.getByLabel("复核备注", { exact: true }).fill("已核对原文与实验");
  await dialog.getByRole("checkbox", { name: "已人工确认" }).check();
  await dialog.getByRole("button", { name: "保存人工复核" }).click();
  await expect(dialog).not.toBeVisible();
  await page.reload();
  await expect(page.getByText("人工备注：已核对原文与实验")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("review-desktop.png") });
  await page.getByRole("button", { name: "评审意见", exact: true }).click();
  await page.getByText("相关工作对比", { exact: true }).click();
  await page.getByLabel("文献 1", { exact: true }).fill("Baseline 2025");
  await page.getByRole("checkbox", { name: /我同意将论文和相关工作/ }).check();
  await page.getByRole("button", { name: "对比相关工作", exact: true }).click();
  await expect(page.getByText("已比较用户提供的相关工作")).toBeVisible();
  await page.getByRole("button", { name: "修改稿与导出", exact: true }).click();
  await page
    .getByLabel("修改稿 PDF", { exact: true })
    .setInputFiles(fixture("frontend-revision.pdf"));
  await page.getByRole("checkbox", { name: /我同意将修改稿/ }).check();
  await page.getByRole("button", { name: "上传并复审" }).click();
  await expect(page.getByText(/复审未完成/)).toBeVisible({ timeout: 15000 });
  await page.reload();
  await page.getByRole("button", { name: "重试复审", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "frontend-revision.pdf" }),
  ).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "确认问题匹配", exact: true }).click();
  await expect(page.getByText("已人工确认问题匹配")).toBeVisible();
  await page.reload();
  await expect(page.getByText("已人工确认问题匹配")).toBeVisible();
  const pdf = await page.request.get(
    (await page
      .getByRole("link", { name: "查看修改稿 PDF" })
      .getAttribute("href")) ?? "",
  );
  expect(pdf.status()).toBe(200);
  await page.setViewportSize({ width: 390, height: 844 });
  await fits(page);
  await page.screenshot({ path: testInfo.outputPath("revision-mobile.png") });
  await page.getByRole("button", { name: "重新评审", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("checkbox", { name: /我同意/ })
    .check();
  await page.getByRole("button", { name: "开始模拟评审", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: "评审意见", exact: true }).click();
  await expect(progress).not.toBeChecked({ timeout: 15000 });
  expect(errors).toEqual([]);
});

test("code upload, selected lines, joint citations and conversation CRUD", async ({
  page,
}, testInfo) => {
  await home(page, "frontend-code.pdf");
  await page.getByRole("button", { name: "生成讲解", exact: true }).click();
  await expect(page.getByRole("heading", { name: "测试要点" })).toBeVisible({
    timeout: 15000,
  });
  await page.getByRole("tab", { name: "追问", exact: true }).click();
  await page.getByRole("button", { name: "新建会话", exact: true }).click();
  await page.getByRole("button", { name: "重命名", exact: true }).click();
  await page.getByLabel("会话名称", { exact: true }).fill("实现核对");
  await page.getByRole("button", { name: "保存名称" }).click();
  await page.reload();
  await expect(
    page.getByRole("combobox", { name: "会话", exact: true }),
  ).toContainText("实现核对");
  await page.getByRole("tab", { name: "代码", exact: true }).click();
  await page
    .getByLabel("源码 ZIP（最多 30MB）")
    .setInputFiles(fixture("code.zip"));
  await page.getByRole("button", { name: "保存代码", exact: true }).click();
  await expect(page.getByLabel("代码文件", { exact: true })).toContainText(
    "main.py",
  );
  await page.getByRole("button", { name: "选择第 2 行", exact: true }).click();
  await page.getByRole("button", { name: "就选中代码提问" }).click();
  await expect(page.getByText(/代码选区：main.py/)).toBeVisible();
  const requestPromise = page.waitForRequest(
    (r) => r.url().endsWith("/code/qa") && r.method() === "POST",
  );
  await page
    .getByRole("textbox", { name: "追问", exact: true })
    .fill("这个函数如何实现准确率？");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  expect((await requestPromise).postDataJSON().selected_code.start_line).toBe(
    2,
  );
  await expect(
    page.getByText("已结合论文和代码回答", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("已结合论文和代码回答", { exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "助手与设置", exact: true }).click();
  await page.getByRole("button", { name: /main.py · L1/ }).click();
  await expect(page.getByLabel("代码内容", { exact: true })).toBeVisible();
  await fits(page);
  await page.screenshot({ path: testInfo.outputPath("code-mobile.png") });
  await page.getByRole("button", { name: "助手与设置", exact: true }).click();
  await page.getByRole("button", { name: "删除会话", exact: true }).click();
  await page.getByRole("button", { name: "确认删除会话" }).click();
  await expect(page.getByText("从一个具体问题开始")).toBeVisible();
});

test("PDF selection and page scope work without a generated lecture", async ({
  page,
}) => {
  const created = await page.request.post(
    "http://127.0.0.1:8001/api/projects",
    {
      multipart: {
        mode: "peer_review",
        privacy_ack: "true",
        pdf: {
          name: "selection.pdf",
          mimeType: "application/pdf",
          buffer: readFileSync(fixture("frontend-selection.pdf")),
        },
      },
    },
  );
  expect(created.status()).toBe(201);
  const project = (await created.json()).project;
  await page.goto(`/p/${project.project_id}/read?view=qa`);
  await expect(
    page.locator(".react-pdf__Page__textContent span").first(),
  ).toBeVisible();
  await page.locator(".react-pdf__Page__textContent").evaluate((node) => {
    const range = document.createRange();
    range.selectNodeContents(node);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
  });
  await page.getByRole("button", { name: "就选中原文提问" }).click();
  await expect(page.getByText(/第 1 页选区：/)).toBeVisible();
  const selected = page.waitForRequest(
    (r) => r.url().endsWith("/qa") && r.method() === "POST",
  );
  await page
    .getByRole("textbox", { name: "追问", exact: true })
    .fill("解释选中内容");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  expect((await selected).postDataJSON().selection.page).toBe(1);
  await expect(page.getByText("已保存回答 1", { exact: true })).toBeVisible();
  await page.getByRole("checkbox", { name: /仅依据当前第 1 页/ }).check();
  const scoped = page.waitForRequest(
    (r) => r.url().endsWith("/qa") && r.method() === "POST",
  );
  await page
    .getByRole("textbox", { name: "追问", exact: true })
    .fill("当前页介绍什么？");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  expect((await scoped).postDataJSON().page_scope).toBe(1);
  await expect(page.getByText("已保存回答 2", { exact: true })).toBeVisible();
});

test("home report file mode, project rename and confirmed deletion", async ({
  page,
}) => {
  await home(page, "frontend-selection.pdf");
  await page.getByRole("radio", { name: "审计一份报告", exact: true }).click();
  await page.getByRole("radio", { name: "上传文件", exact: true }).click();
  await page.getByLabel("报告文件（.txt / .md / .pptx）").setInputFiles({
    name: "report.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("The measured accuracy is 95 percent."),
  });
  await expect(page.getByText(/可审计文本/)).toBeVisible();
  await page.getByRole("button", { name: "开始审计", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "论断详情", exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await page
    .getByRole("button", { name: "Frontend Selection", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "项目标题", exact: true })
    .fill("待删除验收项目");
  await page.getByRole("button", { name: "保存标题" }).click();
  await expect(
    page.getByRole("button", { name: "待删除验收项目", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "待删除验收项目", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "删除 待删除验收项目", exact: true })
    .click();
  await page.getByRole("button", { name: "永久删除", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("link", { name: /待删除验收项目/ })).toHaveCount(
    0,
  );
});
