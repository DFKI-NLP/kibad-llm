/**
 * Syntax-level guard for the eval-dashboard main entry module.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const MAIN_JS_URL = new URL("../../../../docs/eval-dashboard/assets/js/main.js", import.meta.url);
const MAIN_JS_PATH = fileURLToPath(MAIN_JS_URL);

test("main.js parses successfully under Node's syntax checker", () => {
  const stdout = execFileSync(process.execPath, ["--check", MAIN_JS_PATH], {
    encoding: "utf-8",
  });
  assert.equal(stdout, "");
});
