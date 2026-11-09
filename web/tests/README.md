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
