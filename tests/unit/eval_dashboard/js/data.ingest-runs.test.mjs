/**
 * Browser-free logic tests for the eval-dashboard shared run-ingestion helpers.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  createConflictingPredictionIdError,
  discoverRunDirectories,
  getPredictionContentSignature,
  ingestRunEntries,
  isPredictRunDir,
} from "../../../../docs/eval-dashboard/assets/js/data/ingest-runs.js";

function readFixtureText(relativePath) {
  return readFileSync(new URL(`../../../fixtures/eval_dashboard/${relativePath}`, import.meta.url), "utf8");
}

/**
 * Ensure the shared ingestion boundary keeps run-directory discovery, `predict/` exclusion, and
 * missing-job accounting centralized in one place.
 */
test("ingest-runs discovers candidate run directories and excludes predict trees", () => {
  const discovery = discoverRunDirectories([
    { path: "logs/evaluate/run_a/.hydra/overrides.yaml" },
    { path: "logs/evaluate/run_a/job_return_value.json" },
    { path: "logs/evaluate/run_b/.hydra/overrides.yaml" },
    { path: "logs/predict/run_c/.hydra/overrides.yaml" },
    { path: "logs/predict/run_c/job_return_value.json" },
  ]);

  assert.deepEqual(discovery.candidateRunDirs, ["logs/evaluate/run_a"]);
  assert.equal(discovery.skippedMissingJob, 1);
  assert.equal(discovery.skippedPredictRuns, 1);
  assert.equal(isPredictRunDir("logs/predict/run_c"), true);
  assert.equal(isPredictRunDir("logs/evaluate/run_a"), false);
});

/**
 * Ensure the shared ingestion boundary produces canonical additions and summary counts for valid
 * curated fixture inputs.
 */
test("ingest-runs converts valid entries into canonical prediction and evaluation additions", () => {
  const result = ingestRunEntries([
    {
      path: "fixture/run_v2/job_return_value.json",
      text: readFixtureText("run_v2/job_return_value.json"),
    },
    {
      path: "fixture/run_v2/.hydra/overrides.yaml",
      text: readFixtureText("run_v2/.hydra/overrides.yaml"),
    },
  ]);

  assert.equal(result.summary.candidateRunDirs, 1);
  assert.equal(result.summary.loadedCount, 1);
  assert.equal(result.failures.length, 0);
  assert.equal(result.evaluationAdditions.length, 1);
  assert.deepEqual(Object.keys(result.predictionAdditions), [
    "predictions/380_organism_trends/2026-02-24_22-06-17/2026-02-24_22-06-18_939465/predictions.jsonl",
  ]);
});

/**
 * Ensure duplicate run detection remains part of the shared ingestion boundary.
 */
test("ingest-runs skips already loaded run directories", () => {
  const entries = [
    {
      path: "fixture/run_v0/job_return_value.json",
      text: readFixtureText("run_v0/job_return_value.json"),
    },
    {
      path: "fixture/run_v0/.hydra/overrides.yaml",
      text: readFixtureText("run_v0/.hydra/overrides.yaml"),
    },
  ];

  const result = ingestRunEntries(entries, {
    existingEvaluations: [{ runDir: "fixture/run_v0" }],
  });

  assert.equal(result.summary.loadedCount, 0);
  assert.equal(result.summary.skippedDuplicate, 1);
  assert.equal(result.evaluationAdditions.length, 0);
});

/**
 * Ensure conflicting prediction ids remain rejected at the shared ingestion boundary rather than in
 * the single-run normalization helper.
 */
test("ingest-runs rejects conflicting prediction payloads for the same prediction id", () => {
  const result = ingestRunEntries([
    {
      path: "fixture/run_a/job_return_value.json",
      text: readFixtureText("conflicting_prediction_ids/run_a/job_return_value.json"),
    },
    {
      path: "fixture/run_a/.hydra/overrides.yaml",
      text: readFixtureText("conflicting_prediction_ids/run_a/.hydra/overrides.yaml"),
    },
    {
      path: "fixture/run_b/job_return_value.json",
      text: readFixtureText("conflicting_prediction_ids/run_b/job_return_value.json"),
    },
    {
      path: "fixture/run_b/.hydra/overrides.yaml",
      text: readFixtureText("conflicting_prediction_ids/run_b/.hydra/overrides.yaml"),
    },
  ]);

  assert.equal(result.summary.loadedCount, 1);
  assert.equal(result.summary.skippedConflictingPredictionId, 1);
  assert.equal(result.failures.length, 1);
  assert.equal(result.failures[0].error?.name, "ConflictingPredictionIdError");
});

/**
 * Ensure the shared ingestion signature helper stays aligned with the previous conflict-detection
 * semantics used in `main.js`.
 */
test("ingest-runs prediction signatures stay stable for equal payloads and differ for conflicts", () => {
  const predictionA = {
    overrides: { seed: "1" },
    jobReturnValue: { output_file: "predictions/example.jsonl", model: "a" },
  };
  const predictionB = {
    overrides: { seed: "1" },
    jobReturnValue: { model: "a", output_file: "predictions/example.jsonl" },
  };
  const predictionC = {
    overrides: { seed: "2" },
    jobReturnValue: { output_file: "predictions/example.jsonl", model: "a" },
  };

  assert.equal(getPredictionContentSignature(predictionA), getPredictionContentSignature(predictionB));
  assert.notEqual(getPredictionContentSignature(predictionA), getPredictionContentSignature(predictionC));
});

/**
 * Ensure the named conflicting-id error keeps the shape the load summary flow expects.
 */
test("ingest-runs exposes the named conflicting prediction id error", () => {
  const error = createConflictingPredictionIdError("predictions/example.jsonl");

  assert.equal(error.name, "ConflictingPredictionIdError");
  assert.equal(error.predictionId, "predictions/example.jsonl");
  assert.match(error.message, /Conflicting prediction payloads/);
});

/**
 * Ensure the shared ingestion boundary keeps the Phase 8 summary accounting for unsupported,
 * missing-prediction-id, and invalid fixtures rather than leaving those counts in `main.js`.
 */
test("ingest-runs classifies unsupported, missing-prediction-id, and invalid fixtures in summary counts", () => {
  const result = ingestRunEntries([
    {
      path: "fixture/unsupported_version/job_return_value.json",
      text: readFixtureText("unsupported_version/job_return_value.json"),
    },
    {
      path: "fixture/unsupported_version/.hydra/overrides.yaml",
      text: readFixtureText("unsupported_version/.hydra/overrides.yaml"),
    },
    {
      path: "fixture/missing_prediction_id/job_return_value.json",
      text: readFixtureText("missing_prediction_id/job_return_value.json"),
    },
    {
      path: "fixture/missing_prediction_id/.hydra/overrides.yaml",
      text: readFixtureText("missing_prediction_id/.hydra/overrides.yaml"),
    },
    {
      path: "fixture/malformed/job_return_value.json",
      text: readFixtureText("malformed/job_return_value.json"),
    },
    {
      path: "fixture/malformed/.hydra/overrides.yaml",
      text: readFixtureText("malformed/.hydra/overrides.yaml"),
    },
  ]);

  assert.equal(result.summary.candidateRunDirs, 3);
  assert.equal(result.summary.loadedCount, 0);
  assert.equal(result.summary.skippedUnsupportedVersion, 1);
  assert.equal(result.summary.skippedMissingPredictionId, 1);
  assert.equal(result.summary.skippedInvalid, 1);
  assert.equal(result.failures.length, 3);
  assert.deepEqual(
    result.failures.map(({ error }) => error?.name).sort(),
    ["MissingPredictionIdError", "SyntaxError", "UnsupportedJobReturnValueVersionError"].sort()
  );
  assert.deepEqual(result.predictionAdditions, {});
  assert.deepEqual(result.evaluationAdditions, []);
});
