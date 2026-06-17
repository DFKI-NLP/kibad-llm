/**
 * Shared load-status, progress, and download-button rendering helpers for the eval dashboard.
 */

/**
 * Format a byte count for compact progress-label display.
 *
 * @param {number} byteCount - The byte count to format.
 * @returns {string} A compact human-readable byte string.
 */
export function formatBytes(byteCount) {
  const value = Number(byteCount || 0);
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const precision = size >= 100 || unitIndex === 0 ? 0 : 1;
  return `${size.toFixed(precision)} ${units[unitIndex]}`;
}

/**
 * Render the current one-line or multi-line load status text.
 *
 * @param {{loadStatus: HTMLElement | null}} domRefs - Captured dashboard DOM refs.
 * @param {string} title - Primary status line.
 * @param {string[]} [details=[]] - Optional extra status lines.
 * @returns {void}
 */
export function renderLoadStatusStage(domRefs, title, details = []) {
  domRefs.loadStatus.textContent = [title, ...details.filter(Boolean)].join("\n");
}

/**
 * Clear the load-progress UI back to its hidden idle state.
 *
 * @param {{loadProgressWrap: HTMLElement | null, loadProgress: HTMLProgressElement | null, loadProgressLabel: HTMLElement | null}} domRefs - Captured dashboard DOM refs.
 * @returns {void}
 */
export function clearLoadProgress(domRefs) {
  domRefs.loadProgressWrap.classList.remove("visible");
  domRefs.loadProgress.value = 0;
  domRefs.loadProgress.max = 1;
  domRefs.loadProgressLabel.textContent = "";
}

/**
 * Render the current load-progress bar state from a plain progress object.
 *
 * @param {{loadProgressWrap: HTMLElement | null, loadProgress: HTMLProgressElement | null, loadProgressLabel: HTMLElement | null}} domRefs - Captured dashboard DOM refs.
 * @param {{completedFiles?: number, totalFiles?: number, completedBytes?: number, totalBytes?: number, label?: string}} [progress={}] - Plain progress data.
 * @returns {void}
 */
export function renderLoadProgress(
  domRefs,
  { completedFiles = 0, totalFiles = 0, completedBytes = 0, totalBytes = 0, label = "" } = {}
) {
  const maxValue = totalBytes > 0 ? totalBytes : Math.max(totalFiles, 1);
  const nextValue = totalBytes > 0 ? completedBytes : completedFiles;
  domRefs.loadProgressWrap.classList.add("visible");
  domRefs.loadProgress.max = maxValue;
  domRefs.loadProgress.value = Math.min(nextValue, maxValue);
  const fileText = totalFiles > 0 ? `${completedFiles}/${totalFiles} files` : `${completedFiles} files`;
  const byteText = totalBytes > 0 ? ` | ${formatBytes(completedBytes)} / ${formatBytes(totalBytes)}` : "";
  domRefs.loadProgressLabel.textContent = [label, `${fileText}${byteText}`].filter(Boolean).join(" | ");
}

/**
 * Render the summary emitted after a shared-ingestion run completes.
 *
 * @param {{loadStatus: HTMLElement | null}} domRefs - Captured dashboard DOM refs.
 * @param {object} summaryView - Plain summary values for the status block.
 * @param {string[]} summaryView.loadedSources - Loaded source labels.
 * @param {number} summaryView.totalEvaluations - Total evaluations in canonical state.
 * @param {number} summaryView.candidateRunDirs - Candidate run count.
 * @param {number} summaryView.loadedCount - Newly loaded run count.
 * @param {number} summaryView.skippedDuplicate - Duplicate-run skip count.
 * @param {number} summaryView.skippedPredictRuns - Predict-run skip count.
 * @param {number} summaryView.skippedMissingJob - Missing-job skip count.
 * @param {number} summaryView.skippedUnsupportedVersion - Unsupported-version skip count.
 * @param {number} summaryView.skippedInvalid - Invalid-input skip count.
 * @param {number} summaryView.skippedMissingPredictionId - Missing-prediction-id skip count.
 * @param {number} summaryView.skippedConflictingPredictionId - Conflicting-prediction-id skip count.
 * @returns {void}
 */
export function renderLoadStatusSummary(
  domRefs,
  {
    loadedSources,
    totalEvaluations,
    candidateRunDirs,
    loadedCount,
    skippedDuplicate,
    skippedPredictRuns,
    skippedMissingJob,
    skippedUnsupportedVersion,
    skippedInvalid,
    skippedMissingPredictionId,
    skippedConflictingPredictionId,
  }
) {
  domRefs.loadStatus.textContent = [
    `Loaded sources (${loadedSources.length}): ${loadedSources.join(", ")}`,
    `Skipped (is predict run): ${skippedPredictRuns}`,
    `Candidate evaluation runs: ${candidateRunDirs}`,
    `New evaluation runs loaded: ${loadedCount}`,
    `Skipped (already loaded): ${skippedDuplicate}`,
    `Evaluation runs loaded: ${totalEvaluations}`,
    `Skipped (missing job_return_value.json): ${skippedMissingJob}`,
    `Skipped (missing prediction.job_return_value.output_file): ${skippedMissingPredictionId}`,
    `Skipped (conflicting prediction ids): ${skippedConflictingPredictionId}`,
    `Skipped (unsupported data version): ${skippedUnsupportedVersion}`,
    `Skipped (invalid JSON/YAML): ${skippedInvalid}`,
  ].join("\n");
}

/**
 * Render the idle download button label based on the number of visible figures.
 *
 * @param {HTMLButtonElement | null} buttonElement - The download button element.
 * @param {number} figureCount - The number of visible exportable figures.
 * @returns {void}
 */
export function renderDownloadFiguresButtonState(buttonElement, figureCount) {
  buttonElement.disabled = figureCount === 0;
  buttonElement.textContent = figureCount > 0 ? `Download Figures (${figureCount})` : "Download Figures";
}

/**
 * Render the idle data-download button label based on the number of exportable plots.
 *
 * This mirrors the figure-download button contract while counting active plot
 * payloads instead of visible SVG cards.
 *
 * @param {HTMLButtonElement | null} buttonElement - The download button element.
 * @param {number} plotCount - The number of plots with downloadable data.
 * @returns {void}
 */
export function renderDownloadDataButtonState(buttonElement, plotCount) {
  buttonElement.disabled = plotCount === 0;
  buttonElement.textContent = plotCount > 0 ? `Download Data (${plotCount})` : "Download Data";
}

/**
 * Put the download button into its temporary busy state.
 *
 * @param {HTMLButtonElement | null} buttonElement - The download button element.
 * @param {string} [busyLabel="Preparing figures..."] - Busy-state label text.
 * @returns {void}
 */
export function setDownloadFiguresButtonBusy(buttonElement, busyLabel = "Preparing figures...") {
  buttonElement.disabled = true;
  buttonElement.textContent = busyLabel;
}
