/**
 * Browser-free logic tests for the eval-dashboard run-normalization helpers.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { parseOverridesYaml } from "../../../../docs/eval-dashboard/assets/js/data/parse-overrides.js";
import {
  getNormalizedPredictionFromJobReturnValue,
  getMetricTypeForExperiment,
  getPredictionIdFromNormalizedPrediction,
  normalizeImportedJobReturnValue,
} from "../../../../docs/eval-dashboard/assets/js/data/normalize.js";

function readFixtureText(relativePath) {
  return readFileSync(new URL(`../../../fixtures/eval_dashboard/${relativePath}`, import.meta.url), "utf8");
}

function readFixtureJson(relativePath) {
  return JSON.parse(readFixtureText(relativePath));
}

function readFixtureOverrides(fixtureName) {
  return parseOverridesYaml(readFixtureText(`${fixtureName}/.hydra/overrides.yaml`));
}

/**
 * Ensure version-0 fixtures normalize to the canonical dashboard shape while preserving
 * metric-type inference from `experiment/evaluate` overrides.
 */
test("normalize maps version-0 fixtures to the canonical run shape", () => {
  const payload = readFixtureJson("run_v0/job_return_value.json");
  const overrides = readFixtureOverrides("run_v0");

  const normalized = normalizeImportedJobReturnValue(payload, overrides);

  assert.deepEqual(Object.keys(normalized).sort(), ["evaluation", "prediction"]);
  assert.equal(normalized.prediction.jobReturnValue.output_file, payload.prediction.job_return_value.output_file);
  assert.deepEqual(normalized.prediction.overrides, payload.prediction.overrides);
  assert.deepEqual(normalized.evaluation.overrides, overrides);
  assert.deepEqual(normalized.evaluation.jobReturnValue, {
    version: 0,
    type: "F1MicroMultipleFieldsMetric",
  });
  assert.ok("ALL" in normalized.evaluation.data);
  assert.ok(!("prediction" in normalized.evaluation.data));
});

/**
 * Ensure version-1 fixtures keep the same canonical outer shape while excluding the top-level
 * version field from evaluation data.
 */
test("normalize maps version-1 fixtures to the canonical run shape", () => {
  const payload = readFixtureJson("run_v1/job_return_value.json");
  const overrides = readFixtureOverrides("run_v0");

  const normalized = normalizeImportedJobReturnValue(payload, overrides);

  assert.deepEqual(normalized.evaluation.jobReturnValue, {
    version: 1,
    type: "F1MicroMultipleFieldsMetric",
  });
  assert.ok("ALL" in normalized.evaluation.data);
  assert.ok(!("prediction" in normalized.evaluation.data));
  assert.ok(!("version" in normalized.evaluation.data));
});

/**
 * Ensure version-2 fixtures copy top-level evaluation metadata into `evaluation.jobReturnValue`
 * while keeping `data` separate.
 */
test("normalize maps version-2 fixtures to the canonical run shape", () => {
  const payload = readFixtureJson("run_v2/job_return_value.json");
  const overrides = readFixtureOverrides("run_v2");

  const normalized = normalizeImportedJobReturnValue(payload, overrides);

  assert.equal(normalized.evaluation.jobReturnValue.version, 2);
  assert.equal(normalized.evaluation.jobReturnValue.type, "ConfusionMatrixCollection");
  assert.deepEqual(normalized.evaluation.data, payload.data);
  assert.ok(!("data" in normalized.evaluation.jobReturnValue));
  assert.ok(!("prediction" in normalized.evaluation.jobReturnValue));
  assert.equal(
    getPredictionIdFromNormalizedPrediction(normalized.prediction),
    payload.prediction.job_return_value.output_file
  );
});

/**
 * Ensure the legacy metric-type inference contract remains frozen during Phase 7 extraction.
 */
test("normalize preserves legacy metric-type inference from experiment names", () => {
  assert.equal(getMetricTypeForExperiment("organism_trends_confusion_matrix_conditional_variable_only"), "ConfusionMatrix");
  assert.equal(getMetricTypeForExperiment("my_error_collector_run"), "ErrorCollector");
  assert.equal(getMetricTypeForExperiment("faktencheck_tpfpfn_variant"), "TpFpFnCollector");
  assert.equal(getMetricTypeForExperiment("faktencheck_core_f1_micro_flat"), "F1MicroMultipleFieldsMetric");
  assert.equal(getMetricTypeForExperiment("something_else"), "unknown");
});

/**
 * Ensure unsupported payload versions still raise the named Phase 7 error.
 */
test("normalize rejects unsupported payload versions with the named error", () => {
  const payload = readFixtureJson("unsupported_version/job_return_value.json");
  const overrides = readFixtureOverrides("unsupported_version");

  assert.throws(
    () => normalizeImportedJobReturnValue(payload, overrides),
    (error) => error?.name === "UnsupportedJobReturnValueVersionError" && error?.jobReturnValueVersion === 99
  );
});

/**
 * Ensure malformed JSON fixtures still fail cleanly at the parse boundary.
 */
test("normalize fixtures keep malformed JSON failures at the JSON parse boundary", () => {
  const malformedText = readFixtureText("malformed/job_return_value.json");

  assert.throws(() => JSON.parse(malformedText), SyntaxError);
});

/**
 * Ensure missing prediction ids keep raising the named error after normalization.
 */
test("normalize raises MissingPredictionIdError for normalized fixtures without output_file", () => {
  const payload = readFixtureJson("missing_prediction_id/job_return_value.json");
  const overrides = readFixtureOverrides("missing_prediction_id");
  const normalized = normalizeImportedJobReturnValue(payload, overrides);

  assert.throws(
    () => getPredictionIdFromNormalizedPrediction(normalized.prediction),
    (error) => error?.name === "MissingPredictionIdError"
  );
});

/**
 * Ensure cross-run prediction-id conflicts remain an ingestion-flow concern rather than a
 * single-run normalization concern during Phase 7.
 */
test("normalize leaves conflicting prediction-id detection to the ingestion boundary", () => {
  const payloadA = readFixtureJson("conflicting_prediction_ids/run_a/job_return_value.json");
  const payloadB = readFixtureJson("conflicting_prediction_ids/run_b/job_return_value.json");
  const overridesA = parseOverridesYaml(
    readFixtureText("conflicting_prediction_ids/run_a/.hydra/overrides.yaml")
  );
  const overridesB = parseOverridesYaml(
    readFixtureText("conflicting_prediction_ids/run_b/.hydra/overrides.yaml")
  );

  const normalizedA = normalizeImportedJobReturnValue(payloadA, overridesA);
  const normalizedB = normalizeImportedJobReturnValue(payloadB, overridesB);

  assert.equal(getPredictionIdFromNormalizedPrediction(normalizedA.prediction), getPredictionIdFromNormalizedPrediction(normalizedB.prediction));
  assert.notDeepEqual(normalizedA.prediction, normalizedB.prediction);
});

/**
 * Ensure non-object top-level payloads continue to fail early.
 */
test("normalize rejects non-object top-level payloads", () => {
  assert.throws(
    () => normalizeImportedJobReturnValue([]),
    /job_return_value\.json must contain a top-level object\./
  );
});

/**
 * Ensure the extracted prediction normalizer keeps returning the canonical empty-object fallback
 * shape when the embedded prediction payload is malformed.
 */
test("normalize prediction helper falls back to empty objects for malformed nested prediction payloads", () => {
  assert.deepEqual(getNormalizedPredictionFromJobReturnValue({ prediction: [] }), {
    jobReturnValue: {},
    overrides: {},
  });
  assert.deepEqual(
    getNormalizedPredictionFromJobReturnValue({
      prediction: {
        job_return_value: [],
        overrides: "not-an-object",
      },
    }),
    {
      jobReturnValue: {},
      overrides: {},
    }
  );
});

/**
 * Ensure version-2 payloads still reject the specific invalid shape that the loader depends on:
 * missing top-level evaluation `data`.
 */
test('normalize rejects version-2 payloads that omit the top-level "data" field', () => {
  assert.throws(
    () => normalizeImportedJobReturnValue({
      version: 2,
      type: "ConfusionMatrixCollection",
      prediction: {
        job_return_value: { output_file: "predictions/example.jsonl" },
        overrides: { seed: "7" },
      },
    }),
    /job_return_value\.json version 2 must contain a top-level "data" field\./
  );
});

/**
 * Ensure prediction-id extraction preserves the pre-refactor normalization contract by trimming
 * whitespace and normalizing non-string scalar values.
 */
test("normalize prediction-id extraction trims and stringifies scalar output_file values", () => {
  assert.equal(
    getPredictionIdFromNormalizedPrediction({
      jobReturnValue: { output_file: "  predictions/example.jsonl  " },
    }),
    "predictions/example.jsonl"
  );
  assert.equal(
    getPredictionIdFromNormalizedPrediction({ jobReturnValue: { output_file: 12345 } }),
    "12345"
  );
});
