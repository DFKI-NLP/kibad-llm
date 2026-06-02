import test from "node:test";
import assert from "node:assert/strict";

import {
  clearLoadProgress,
  formatBytes,
  renderDownloadFiguresButtonState,
  renderLoadProgress,
  renderLoadStatusStage,
  renderLoadStatusSummary,
  setDownloadFiguresButtonBusy,
} from "../../../../docs/eval-dashboard/assets/js/ui/status.js";

function createClassList() {
  return {
    values: new Set(),
    add(...names) {
      names.forEach((name) => this.values.add(name));
    },
    remove(...names) {
      names.forEach((name) => this.values.delete(name));
    },
    contains(name) {
      return this.values.has(name);
    },
  };
}

function createStatusDomRefs() {
  return {
    loadStatus: { textContent: "" },
    loadProgressWrap: { classList: createClassList() },
    loadProgress: { value: 0, max: 0 },
    loadProgressLabel: { textContent: "" },
  };
}

test("formatBytes keeps the dashboard's compact byte-label formatting semantics", () => {
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatBytes(null), "0 B");
  assert.equal(formatBytes(1024), "1.0 KB");
  assert.equal(formatBytes(100 * 1024 * 1024), "100 MB");
});

test("renderLoadStatusStage joins title and non-empty details into the status block", () => {
  const domRefs = createStatusDomRefs();

  renderLoadStatusStage(domRefs, "Loading evaluation runs", ["GitHub source", "", null, "2/4 files"]);
  assert.equal(domRefs.loadStatus.textContent, "Loading evaluation runs\nGitHub source\n2/4 files");
});

test("renderLoadProgress and clearLoadProgress update progress visibility, labels, and clamping", () => {
  const domRefs = createStatusDomRefs();

  renderLoadProgress(domRefs, {
    completedFiles: 5,
    totalFiles: 4,
    completedBytes: 2300,
    totalBytes: 2048,
    label: "Fetching GitHub files",
  });

  assert.equal(domRefs.loadProgressWrap.classList.contains("visible"), true);
  assert.equal(domRefs.loadProgress.max, 2048);
  assert.equal(domRefs.loadProgress.value, 2048);
  assert.equal(
    domRefs.loadProgressLabel.textContent,
    "Fetching GitHub files | 5/4 files | 2.2 KB / 2.0 KB"
  );

  renderLoadProgress(domRefs, { completedFiles: 2, totalFiles: 3, label: "Parsing runs" });
  assert.equal(domRefs.loadProgress.max, 3);
  assert.equal(domRefs.loadProgress.value, 2);
  assert.equal(domRefs.loadProgressLabel.textContent, "Parsing runs | 2/3 files");

  clearLoadProgress(domRefs);
  assert.equal(domRefs.loadProgressWrap.classList.contains("visible"), false);
  assert.equal(domRefs.loadProgress.value, 0);
  assert.equal(domRefs.loadProgress.max, 1);
  assert.equal(domRefs.loadProgressLabel.textContent, "");
});

test("renderLoadStatusSummary preserves the dashboard's multi-line summary contract", () => {
  const domRefs = createStatusDomRefs();

  renderLoadStatusSummary(domRefs, {
    loadedSources: ["local fixtures", "org/repo@main/logs"],
    totalEvaluations: 12,
    candidateRunDirs: 15,
    loadedCount: 7,
    skippedDuplicate: 2,
    skippedPredictRuns: 1,
    skippedMissingJob: 3,
    skippedUnsupportedVersion: 4,
    skippedInvalid: 5,
    skippedMissingPredictionId: 6,
    skippedConflictingPredictionId: 8,
  });

  assert.equal(
    domRefs.loadStatus.textContent,
    [
      "Loaded sources (2): local fixtures, org/repo@main/logs",
      "Skipped (is predict run): 1",
      "Candidate evaluation runs: 15",
      "New evaluation runs loaded: 7",
      "Skipped (already loaded): 2",
      "Evaluation runs loaded: 12",
      "Skipped (missing job_return_value.json): 3",
      "Skipped (missing prediction.job_return_value.output_file): 6",
      "Skipped (conflicting prediction ids): 8",
      "Skipped (unsupported data version): 4",
      "Skipped (invalid JSON/YAML): 5",
    ].join("\n")
  );
});

test("download button helpers switch between idle and busy labels", () => {
  const button = { disabled: false, textContent: "" };

  renderDownloadFiguresButtonState(button, 0);
  assert.equal(button.disabled, true);
  assert.equal(button.textContent, "Download Figures");

  renderDownloadFiguresButtonState(button, 3);
  assert.equal(button.disabled, false);
  assert.equal(button.textContent, "Download Figures (3)");

  setDownloadFiguresButtonBusy(button, "Exporting plots...");
  assert.equal(button.disabled, true);
  assert.equal(button.textContent, "Exporting plots...");

  setDownloadFiguresButtonBusy(button);
  assert.equal(button.textContent, "Preparing figures...");
});
