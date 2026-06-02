/**
 * Browser-free logic tests for the eval-dashboard overrides parser.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { parseOverridesYaml } from "../../../../docs/eval-dashboard/assets/js/data/parse-overrides.js";

function readFixtureText(relativePath) {
  return readFileSync(new URL(`../../../fixtures/eval_dashboard/${relativePath}`, import.meta.url), "utf8");
}

/**
 * Ensure the parser preserves the current accepted Hydra-override list semantics on real fixtures.
 */
test("parse-overrides parses the current fixture override format", () => {
  const overridesText = readFixtureText("run_v0/.hydra/overrides.yaml");

  assert.deepEqual(parseOverridesYaml(overridesText), {
    "dataset.predictions.log": "logs/380_faktencheck_core/predict/multiruns/2026-03-11_16-30-57/11",
    name: "397_faktencheck_core_v1_for_chunking",
    "experiment/evaluate": "faktencheck_core_f1_micro_flat",
    prediction_logs: "logs/380_faktencheck_core/predict",
  });
});

/**
 * Ensure blank lines, comments, malformed lines, and non-list-item lines stay permissively ignored.
 */
test("parse-overrides ignores non-understood lines without raising", () => {
  const text = [
    "",
    "# comment",
    "not a list item",
    "- ",
    "- noequals",
    "- keep=this",
    "  - nested=list-item",
  ].join("\n");

  assert.deepEqual(parseOverridesYaml(text), {
    keep: "this",
    nested: "list-item",
  });
});

/**
 * Ensure the parser strips exactly one leading plus from keys and keeps raw string values.
 */
test("parse-overrides strips one leading plus and preserves raw string values", () => {
  const text = [
    "- +single=value",
    "- ++double=value",
    "- spaced =  value with = signs = kept  ",
  ].join("\n");

  assert.deepEqual(parseOverridesYaml(text), {
    single: "value",
    "+double": "value",
    spaced: "value with = signs = kept",
  });
});
