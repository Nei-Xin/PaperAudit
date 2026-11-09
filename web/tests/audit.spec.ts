import { test, expect, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

async function project(page: Page) {
  await page.goto('/');
  await page.locator('input[type="file"]').first().setInputFiles(fileURLToPath(new URL('./fixtures/reading.pdf', import.meta.url)));
  await page.getByRole('checkbox', { name: /我同意/ }).check();
  await page.getByRole('button', { name: '生成讲解', exact: true }).click();
  await expect(page).toHaveURL(/\/p\/[a-f0-9]+\/read$/);
  await expect(page.getByRole('heading', { name: '测试要点' })).toBeVisible({ timeout: 15000 });
  await page.getByRole('navigation', { name: '项目视图' }).getByRole('link', { name: /审计/ }).click();
}
async function open(page: Page) {
  await page.getByRole('button', { name: '审计报告', exact: true }).click();
  return page.getByRole('dialog', { name: '审计一份报告' });
}

test('pasted audit survives refresh, opens exact result and exports', async ({ page }) => {
  await project(page);
  const dialog = await open(page);
  await dialog.getByRole('textbox', { name: '中文解读内容' }).fill('准确率为95%，这是浏览器粘贴审计测试。');
  await expect(dialog.getByRole('button', { name: '开始审计' })).toBeDisabled();
  await dialog.getByRole('checkbox', { name: /我同意/ }).check();
  await dialog.getByRole('button', { name: '开始审计' }).click();
  await expect(page).toHaveURL(/job=audit-job/);
  await page.reload();
  await expect(page).toHaveURL(/\/audit\/audit-/, { timeout: 15000 });
  await expect(page.getByRole('region', { name: '论断详情', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '报告导出', exact: true }).click();
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('link', { name: '下载 Markdown 报告' }).click()]);
  expect(download.suggestedFilename()).toBe('report.md');
  await page.reload();
  await expect(page.getByRole('link', { name: '下载 Markdown 报告' })).toBeVisible();
});

test('audit failure remains after reload and explicit retry completes', async ({ page }) => {
  await project(page);
  const dialog = await open(page);
  await dialog.getByRole('textbox', { name: '中文解读内容' }).fill('FAIL_ONCE 准确率为95%。');
  await dialog.getByRole('checkbox', { name: /我同意/ }).check();
  await dialog.getByRole('button', { name: '开始审计' }).click();
  await expect(page.getByText('审计未完成：测试审计失败')).toBeVisible({ timeout: 15000 });
  await page.reload();
  await page.getByRole('button', { name: '重试审计' }).click();
  await expect(page).toHaveURL(/\/audit\/audit-/, { timeout: 15000 });
});

test('mobile file preview and current lecture audit', async ({ page }) => {
  await project(page);
  await page.setViewportSize({ width: 390, height: 844 });
  let dialog = await open(page);
  await dialog.getByRole('radio', { name: '上传文件' }).click();
  await dialog.locator('input[type="file"]').setInputFiles({ name: 'report.md', mimeType: 'text/markdown', buffer: Buffer.from('# 结果\n准确率为95%。') });
  await expect(dialog.getByText(/可审计文本/)).toBeVisible();
  await dialog.getByRole('checkbox', { name: /我同意/ }).check();
  await dialog.getByRole('button', { name: '开始审计' }).click();
  await expect(page).toHaveURL(/\/audit\/audit-/, { timeout: 15000 });
  dialog = await open(page);
  await dialog.getByRole('checkbox', { name: '审计当前讲解' }).check();
  await dialog.getByRole('checkbox', { name: /我同意/ }).check();
  await dialog.getByRole('button', { name: '开始审计' }).click();
  await expect(page).toHaveURL(/\/audit\/audit-/, { timeout: 15000 });
  await expect(page.getByRole('combobox', { name: '审计记录' })).toContainText('当前论文讲解');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
});

test('home audit mode submits without generating lecture', async ({ page }) => {
  await page.goto('/');
  await page.locator('input[type="file"]').first().setInputFiles(fileURLToPath(new URL('./fixtures/retry.pdf', import.meta.url)));
  await page.getByRole('radio', { name: '审计一份报告', exact: true }).click();
  await page.getByRole('textbox', { name: '中文解读内容' }).fill('首页审计：准确率为95%。');
  await page.getByRole('checkbox', { name: /我同意/ }).check();
  await page.getByRole('button', { name: '开始审计', exact: true }).click();
  await expect(page).toHaveURL(/\/audit\/audit-/, { timeout: 15000 });
});
