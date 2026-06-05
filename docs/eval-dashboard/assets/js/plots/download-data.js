/**
 * Download-data payload helpers for eval-dashboard plots.
 */

import { sanitizeFigureFilename } from "../utils/text.js";
import { buildJsonSafeNumericPlottingData } from "./bars.js";
import {
  saveBlob,
  triggerBlobDownload,
} from "./export.js";
import { buildJsonSafeMatrixPlottingData } from "./shared-matrix.js";

/**
 * Converts the active plot download source into the public JSON payload.
 *
 * Rendering stores the already-active source objects so it does not spend time
 * converting Maps and point arrays into JSON-safe data unless the user actually
 * downloads the data. This helper preserves the public download schema.
 *
 * @param {object} downloadData - Active plot download source from dashboard state.
 * @returns {object|null} JSON-safe public payload, or null when nothing is downloadable.
 * @throws {Error} If the active plot download source has an unsupported metric family.
 */
export function buildJsonSafeActivePlotDownloadData(downloadData) {
  if (!downloadData || !Array.isArray(downloadData.plots) || downloadData.plots.length === 0) {
    return null;
  }

  const buildData = (plot) => {
    if (downloadData.metric_family === "numeric") {
      return buildJsonSafeNumericPlottingData(plot?.dataSource);
    }
    if (
      downloadData.metric_family === "confusion_matrix" ||
      downloadData.metric_family === "tpfpfn"
    ) {
      return buildJsonSafeMatrixPlottingData(plot?.dataSource);
    }
    throw new Error(
      `Unsupported active plot download metric family: ${downloadData.metric_family || "(missing)"}`
    );
  };

  return {
    metric_family: downloadData.metric_family,
    plot_tab: downloadData.plot_tab,
    plots: downloadData.plots.map((plot) => ({
      metaData: plot?.metaData || {},
      data: buildData(plot),
    })),
  };
}

/**
 * Downloads the current active plot data payload as JSON.
 *
 * This separates browser save/fallback behavior from plot rendering so tests
 * can verify the downloaded JSON without a real browser download.
 *
 * @param {object} options - State and browser dependencies.
 * @returns {Promise<boolean>} True when a save/download was started.
 */
export async function downloadActivePlotData({
  state,
  documentLike = globalThis.document,
  windowLike = globalThis.window,
  urlLike = globalThis.URL,
  setTimeoutLike = globalThis.setTimeout,
  save = saveBlob,
  triggerDownload = (blob, filename) => triggerBlobDownload({ documentLike, urlLike, setTimeoutLike, filename, blob }),
  consoleLike = globalThis.console,
}) {
  const payload = buildJsonSafeActivePlotDownloadData(state?.activePlotDownloadData);
  if (!payload) {
    return false;
  }
  const filenameParts = [
    state?.activeEvalTab,
    payload.plot_tab || "plot-data",
    "data",
  ].filter(Boolean).map((part) => sanitizeFigureFilename(String(part)));
  const suggestedName = `${filenameParts.join("-") || "plot-data"}.json`;
  const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" });
  return save({
    windowLike,
    blob,
    suggestedName,
    types: [{
      description: "JSON data",
      accept: { "application/json": [".json"] },
    }],
    triggerDownload,
    consoleLike,
  });
}

/**
 * Extracts only metadata fields from a plot entry for downloads.
 *
 * Plot entries also carry raw source data (`collections`) or numeric input data
 * (`points`). Downloads store that data separately in `data`, so this helper
 * prevents accidental duplication in exported metadata.
 *
 * @param {object} plotEntry - Plot entry used by the renderer.
 * @returns {object} Plot metadata without embedded data arrays.
 */
export function getDownloadPlotEntryMetadata({
  collections,
  points,
  parts,
  prefix,
  suffix,
  metricRoot,
  metricPrefix,
  metricSuffix,
  ...metadata
} = {}) {
  // TODO: add or also return runDirs? would this work?
  return metadata;
}
