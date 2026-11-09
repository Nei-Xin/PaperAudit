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
