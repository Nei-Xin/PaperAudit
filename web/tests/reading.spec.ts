import { test, expect, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

async function upload(page: Page, fixture = "reading") {
  await page.goto("/");
  await page.locator('input[type="file"]').first().setInputFiles(fileURLToPath(new URL(`./fixtures/${fixture}.pdf`, import.meta.url)));
  await expect(page.getByRole("button", { name: "生成讲解", exact: true })).toBeDisabled();
  await page.getByRole("checkbox", { name: /我同意/ }).check();
  await page.getByRole("button", { name: "生成讲解", exact: true }).click();
  await expect(page).toHaveURL(/\/p\/[a-f0-9]+\/read$/);
}

test("upload → background lecture → question → reload → new conversation → citation", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  await upload(page);
  await expect(page.getByRole("heading", { name: "测试要点" })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("textbox", { name: "追问", exact: true }).fill("研究方法是什么？");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  await expect(page.getByText("已保存回答 1", { exact: true })).toBeVisible();
  const url = page.url();
  await page.reload();
  await expect(page.getByText("已保存回答 1", { exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "会话", exact: true }).selectOption("new");
  await page.getByRole("textbox", { name: "追问", exact: true }).fill("新会话问题");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  await expect(page.getByText("新会话问题", { exact: true }).last()).toBeVisible();
  await expect(page.getByRole("combobox", { name: "会话", exact: true }).locator("option")).toHaveCount(3);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: /↗/ }).first().click();
  await expect(page.locator("canvas").first()).toBeVisible();
  await page.goto(url);
  await expect(page.getByText("已保存回答 1", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("failed generation remains visible after reload and explicit retry completes", async ({ page }) => {
  await upload(page, "retry");
  await expect(page.getByText(/上次任务未完成/)).toBeVisible({ timeout: 15_000 });
  await page.reload();
  await page.getByRole("button", { name: "重试生成讲解", exact: true }).click();
  await expect(page.getByRole("heading", { name: "测试要点" })).toBeVisible({ timeout: 15_000 });
});

test("failed question retains input and settings can be saved without returning the key", async ({ page }) => {
  await upload(page);
  await expect(page.getByRole("heading", { name: "测试要点" })).toBeVisible();
  await page.getByRole("textbox", { name: "追问", exact: true }).fill("触发失败");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  await expect(page.getByText("输入内容无法处理，请检查文件和参数。")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "追问", exact: true })).toHaveValue("触发失败");
  await page.getByRole("button", { name: /已配置 ·/ }).click();
  await page.getByRole("textbox", { name: "模型", exact: true }).fill("updated-test-model");
  await page.getByRole("button", { name: "保存设置" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", { name: /已配置 · updated-test-model/ })).toBeVisible();
});


test("detailed lecture keeps old content on failure and explicit retry replaces it", async ({ page }) => {
  await upload(page, "regenerate");
  const summary = page.getByRole("region", { name: "阅读导览" });
  await expect(summary.getByText("测试论文讲解", { exact: true })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "重新生成详细讲解", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "重新生成详细讲解", exact: true });
  await expect(dialog.getByRole("button", { name: "开始生成", exact: true })).toBeDisabled();
  await dialog.getByRole("checkbox", { name: /我同意/ }).check();
  await dialog.getByRole("button", { name: "开始生成", exact: true }).click();
  await expect(page.getByText("生成期间可继续阅读当前讲解")).toBeVisible();
  await expect(summary.getByText("测试论文讲解", { exact: true })).toBeVisible();
  await expect(page.getByText(/详细讲解未完成，当前讲解已保留/)).toBeVisible({ timeout: 15_000 });
  await page.reload();
  await expect(summary.getByText("测试论文讲解", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "重试详细讲解", exact: true }).click();
  await expect(summary.getByText("重新生成的详细讲解", { exact: true })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("详细讲解的新解释，已通过质量检查。", { exact: true })).toBeVisible();
  await page.reload();
  await expect(summary.getByText("重新生成的详细讲解", { exact: true })).toBeVisible();
  await expect(page.getByText(/详细讲解未完成/)).toHaveCount(0);
  await page.getByRole("radio", { name: "全部章节", exact: true }).click();
  await expect(page.getByRole("heading", { name: /研究方法.*1 点/ })).toBeVisible();
});
