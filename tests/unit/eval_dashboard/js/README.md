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
- Add new extracted logic tests as additional `*.test.mjs` files in this directory so the default command and CI job pick them up automatically.
