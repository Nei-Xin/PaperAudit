# Frontend layout regression checks

Run from `web/`:

```sh
npm ci
npx playwright install chromium
npm run test:layout
```

To use an installed Chrome instead of downloading Chromium:

```sh
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:layout
```

The suite starts a read-only Vite instance on port 5180, intercepts API requests,
and uses the generated sample JSON/PDF in `fixtures/`. It does not need project
exports, a backend, model credentials, or production data. Non-GET API requests
fail the test.

Coverage includes seven desktop/mobile/short-screen sizes, navigation hit testing,
review idle computations and ordinary clicks, sidebar keyboard behavior, reading
pane state, citation navigation, PDF enlargement, claim selection, filter controls,
modal footer visibility, and long filenames. Screenshot/trace artifacts are saved
under `test-results/` for failures.

## 阅读流程集成测试

```sh
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:reading
```

使用 `playwright.workflow.config.ts` 启动 Vite 5181 和 FastAPI 8001，真实 HTTP 接口、临时文件库和模型替身。
测试上传到讲解自动刷新、问答保存/重载、新会话、移动端引用跳转、生成失败后重试、追问失败保留输入和设置保存。
不会读写正式项目或调用真实模型。布局测试和流程测试使用独立输出子目录。

后端接口变更后执行 `npm run gen:api`。该命令只导出 schema，不启动服务或访问项目库。

审计集成测试也包含在 `npm run test:reading` 中（`audit.spec.ts`）。使用相同临时服务，覆盖粘贴报告、文件预解析、当前讲解、首页模式、失败重试、自动跳转与导出。
