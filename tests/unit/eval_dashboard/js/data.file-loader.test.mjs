/**
 * Browser-free logic tests for the eval-dashboard local file-loader helpers.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  collectLocalEvaluationEntries,
  deriveLocalSourceLabel,
  isRelevantEvaluationFilePath,
} from "../../../../docs/eval-dashboard/assets/js/data/file-loader.js";

/**
 * Ensure the local-file adapter keeps the current path filter contract for relevant run files.
 */
test("file-loader recognizes relevant evaluation file paths", () => {
  assert.equal(isRelevantEvaluationFilePath("run_a/.hydra/overrides.yaml"), true);
  assert.equal(isRelevantEvaluationFilePath("run_a/job_return_value.json"), true);
  assert.equal(isRelevantEvaluationFilePath("run_a/metrics.json"), false);
  assert.equal(isRelevantEvaluationFilePath("predict/run_b/job_return_value.jsonl"), false);
});

/**
 * Ensure the derived local source label remains the first selected top-level folder name.
 */
test("file-loader derives the local source label from the first browser-relative path", () => {
  assert.equal(
    deriveLocalSourceLabel([
      { webkitRelativePath: "logs/run_a/job_return_value.json" },
      { webkitRelativePath: "logs/run_a/.hydra/overrides.yaml" },
    ]),
    "logs"
  );
  assert.equal(deriveLocalSourceLabel([]), "selected folder");
});

/**
 * Ensure the local-file adapter filters irrelevant paths and returns raw ingestion entries only for
 * the supported dashboard files.
 */
test("file-loader collects only relevant local evaluation entries", async () => {
  const files = [
    {
      webkitRelativePath: "fixtures/run_a/job_return_value.json",
      text: async () => '{"version": 2}',
    },
    {
      webkitRelativePath: "fixtures/run_a/.hydra/overrides.yaml",
      text: async () => "- name=example",
    },
    {
      webkitRelativePath: "fixtures/run_a/ignored.txt",
      text: async () => "ignore me",
    },
  ];

  const result = await collectLocalEvaluationEntries(files);

  assert.equal(result.rootLabel, "fixtures");
  assert.deepEqual(result.entries, [
    {
      path: "fixtures/run_a/job_return_value.json",
      text: '{"version": 2}',
    },
    {
      path: "fixtures/run_a/.hydra/overrides.yaml",
      text: "- name=example",
    },
  ]);
});
