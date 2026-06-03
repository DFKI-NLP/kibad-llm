# Eval-dashboard JS logic tests

This directory is the long-term home for browser-free eval-dashboard JavaScript logic tests.

## Default command

Run the extracted dashboard JS logic tests with Node's built-in test runner:

```bash
node --test tests/unit/eval_dashboard/js/*.test.mjs
```

## Notes

- Keep tests DOM-free in this phase range; they should cover extracted pure helpers and later selector/data modules.
- Runtime dashboard modules under `docs/eval-dashboard/assets/js/` are treated as ES modules via the colocated `package.json` manifest.
- Keep test files flat in this directory so `node --test tests/unit/eval_dashboard/js/*.test.mjs` remains stable without recursive globbing.
- Prefer module-scoped filenames such as `main.syntax.test.mjs`, `utils.flatten.test.mjs`, `state.store.test.mjs`, `state.selectors.test.mjs`, `data.normalize.test.mjs`, `data.parse-overrides.test.mjs`, `data.ingest-runs.test.mjs`, `data.file-loader.test.mjs`, `data.git-loader.test.mjs`, `ui.dom.test.mjs`, `ui.status.test.mjs`, `ui.table-shared.test.mjs`, `ui.controls.test.mjs`, `ui.eval-json-pane.test.mjs`, `ui.tabs.test.mjs`, `ui.prediction-table.test.mjs`, `ui.evaluation-table.test.mjs`, `plots.shared.test.mjs`, `plots.confusion.test.mjs`, `plots.tpfpfn.test.mjs`, `plots.export.test.mjs`, and `browser.session.test.mjs`.
- `main.syntax.test.mjs` is the lightweight guard that runs `node --check` on `docs/eval-dashboard/assets/js/main.js` so the CI JS job catches syntax-only breakage in the dashboard entry module.
- Add new extracted logic tests as additional `*.test.mjs` files in this directory so the default command and CI job pick them up automatically.
