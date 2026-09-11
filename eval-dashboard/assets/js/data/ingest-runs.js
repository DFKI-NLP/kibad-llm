/**
 * Shared raw-entry ingestion helpers for eval-dashboard run imports.
 */

import { flattenObject } from "../utils/flatten.js";
import { getEvaluationRunId, getRunIdFromImportedSources } from "../utils/runs.js";
import { getStableObjectSignature } from "../utils/values.js";
import { parseOverridesYaml } from "./parse-overrides.js";
import {
  getPredictionIdFromNormalizedPrediction,
  normalizeImportedJobReturnValue,
} from "./normalize.js";

const OVERRIDES_SUFFIX = "/.hydra/overrides.yaml";
const JOB_RETURN_VALUE_SUFFIX = "/job_return_value.json";

/**
 * Check whether a raw entry path points to a Hydra overrides file.
 *
 * @param {string} path - Raw entry path.
 * @returns {boolean} Whether the path is a supported overrides file.
 */
export function isHydraOverridesPath(path) {
  return /(^|\/)\.hydra\/overrides\.yaml$/.test(path);
}

/**
 * Check whether a raw entry path points to a job-return-value file.
 *
 * @param {string} path - Raw entry path.
 * @returns {boolean} Whether the path is a supported job-return-value file.
 */
export function isJobReturnValuePath(path) {
  return /(^|\/)job_return_value\.json$/.test(path);
}

/**
 * Check whether a run directory is part of a prediction-only tree that should be excluded.
 *
 * @param {string} runDir - Candidate run directory.
 * @returns {boolean} Whether the run directory belongs to `predict/`.
 */
export function isPredictRunDir(runDir) {
  return /(^|\/)predict(\/|$)/.test(runDir);
}

/**
 * Create the named error used when two runs reuse one prediction id with conflicting payloads.
 *
 * @param {string} predictionId - Conflicting canonical prediction id.
 * @returns {Error & {name: string, predictionId: string}} Named conflicting-id error.
 */
export function createConflictingPredictionIdError(predictionId) {
  const error = new Error(`Conflicting prediction payloads for prediction id: ${predictionId}`);
  error.name = "ConflictingPredictionIdError";
  error.predictionId = predictionId;
  return error;
}

/**
 * Build a stable content signature for one normalized prediction payload.
 *
 * @param {{overrides?: object, jobReturnValue?: object} | null | undefined} prediction - Canonical prediction payload.
 * @returns {string} Stable prediction content signature.
 */
export function getPredictionContentSignature(prediction) {
  return getStableObjectSignature({
    ...flattenObject(prediction?.overrides || {}, "prediction.overrides"),
    ...flattenObject(prediction?.jobReturnValue || {}, "prediction.job_return_value"),
  });
}

/**
 * Discover run directories from raw `{ path, text }` entries and compute ingestion-relevant groupings.
 *
 * @param {Array<{path?: unknown}>} entries - Raw source entries.
 * @returns {{hydraRunDirs: string[], jobRunDirs: string[], candidateRunDirs: string[], skippedPredictRuns: number, skippedMissingJob: number}} Discovered run-directory information.
 */
export function discoverRunDirectories(entries) {
  const hydraRunDirs = new Set();
  const jobRunDirs = new Set();

  for (const entry of entries || []) {
    const relativePath = String(entry?.path || "");
    if (isHydraOverridesPath(relativePath)) {
      hydraRunDirs.add(relativePath.slice(0, -OVERRIDES_SUFFIX.length));
    }
    if (isJobReturnValuePath(relativePath)) {
      jobRunDirs.add(relativePath.slice(0, -JOB_RETURN_VALUE_SUFFIX.length));
    }
  }

  const allSeenRunDirs = new Set([...hydraRunDirs, ...jobRunDirs]);
  let skippedPredictRuns = 0;
  for (const runDir of allSeenRunDirs) {
    if (isPredictRunDir(runDir)) {
      skippedPredictRuns += 1;
    }
  }

  let skippedMissingJob = 0;
  for (const runDir of hydraRunDirs) {
    if (!jobRunDirs.has(runDir) && !isPredictRunDir(runDir)) {
      skippedMissingJob += 1;
    }
  }

  const candidateRunDirs = Array.from(hydraRunDirs)
    .filter((runDir) => jobRunDirs.has(runDir) && !isPredictRunDir(runDir))
    .sort((left, right) => left.localeCompare(right));

  return {
    hydraRunDirs: Array.from(hydraRunDirs).sort((left, right) => left.localeCompare(right)),
    jobRunDirs: Array.from(jobRunDirs).sort((left, right) => left.localeCompare(right)),
    candidateRunDirs,
    skippedPredictRuns,
    skippedMissingJob,
  };
}

/**
 * Ingest raw `{ path, text }` entries into canonical prediction and evaluation additions.
 *
 * @param {Array<{path?: unknown, text?: unknown}>} entries - Raw source entries.
 * @param {{existingPredictions?: Record<string, {overrides?: object, jobReturnValue?: object}> | Map<string, {overrides?: object, jobReturnValue?: object}>, existingEvaluations?: Array<{runId?: unknown, runDir?: unknown}>}} [options={}] - Existing dashboard data used for duplicate detection.
 * @returns {Promise<{candidateRunDirs: string[], predictionAdditions: Record<string, {jobReturnValue: Record<string, unknown>, overrides: Record<string, unknown>}>, evaluationAdditions: Array<{runId: string, runDir: string, predictionId: string, jobReturnValue: Record<string, unknown>, overrides: Record<string, string>, data: unknown}>, failures: Array<{runDir: string, error: Error}>, summary: {candidateRunDirs: number, loadedCount: number, skippedSameContent: number, skippedPredictRuns: number, skippedMissingJob: number, skippedUnsupportedVersion: number, skippedInvalid: number, skippedMissingPredictionId: number, skippedConflictingPredictionId: number}}>} Ingestion result.
 */
export async function ingestRunEntries(entries, options = {}) {
  const normalizedEntries = Array.isArray(entries) ? entries : [];
  const { candidateRunDirs, skippedPredictRuns, skippedMissingJob } = discoverRunDirectories(normalizedEntries);
  const byPath = new Map();
  for (const entry of normalizedEntries) {
    const relativePath = String(entry?.path || "");
    if (!relativePath) {
      continue;
    }
    byPath.set(relativePath, String(entry?.text || ""));
  }

  const existingPredictions = options.existingPredictions instanceof Map
    ? new Map(options.existingPredictions)
    : new Map(Object.entries(options.existingPredictions || {}));
  const knownRunIds = new Set(
    (options.existingEvaluations || [])
      .map((evaluation) => getEvaluationRunId(evaluation))
      .filter(Boolean)
  );
  const predictionAdditions = new Map();
  const evaluationAdditions = [];
  const failures = [];
  let loadedCount = 0;
  let skippedSameContent = 0;
  let skippedUnsupportedVersion = 0;
  let skippedInvalid = 0;
  let skippedMissingPredictionId = 0;
  let skippedConflictingPredictionId = 0;

  for (const runDir of candidateRunDirs) {
    const jobText = byPath.get(`${runDir}${JOB_RETURN_VALUE_SUFFIX}`);
    const overridesText = byPath.get(`${runDir}${OVERRIDES_SUFFIX}`);
    if (!jobText || !overridesText) {
      continue;
    }

    try {
      const job_return_value = JSON.parse(jobText);
      const evaluationOverrides = parseOverridesYaml(overridesText);
      const runId = await getRunIdFromImportedSources(job_return_value, evaluationOverrides);
      if (knownRunIds.has(runId)) {
        skippedSameContent += 1;
        continue;
      }
      const normalizedRun = normalizeImportedJobReturnValue(job_return_value, evaluationOverrides);
      const predictionId = getPredictionIdFromNormalizedPrediction(normalizedRun.prediction);
      const knownPrediction = predictionAdditions.get(predictionId) || existingPredictions.get(predictionId);
      const hasConflictingPrediction = (
        knownPrediction &&
        getPredictionContentSignature(knownPrediction) !== getPredictionContentSignature(normalizedRun.prediction)
      );
      if (hasConflictingPrediction) {
        skippedConflictingPredictionId += 1;
        failures.push({ runDir, error: createConflictingPredictionIdError(predictionId) });
        continue;
      }
      if (!knownPrediction) {
        predictionAdditions.set(predictionId, normalizedRun.prediction);
      }

      evaluationAdditions.push({
        runId,
        runDir,
        predictionId,
        jobReturnValue: normalizedRun.evaluation.jobReturnValue,
        overrides: normalizedRun.evaluation.overrides,
        data: normalizedRun.evaluation.data,
      });
      knownRunIds.add(runId);
      loadedCount += 1;
    } catch (error) {
      if (error?.name === "UnsupportedJobReturnValueVersionError") {
        skippedUnsupportedVersion += 1;
      } else if (error?.name === "MissingPredictionIdError") {
        skippedMissingPredictionId += 1;
      } else {
        skippedInvalid += 1;
      }
      failures.push({ runDir, error });
    }
  }

  return {
    candidateRunDirs,
    predictionAdditions: Object.fromEntries(predictionAdditions),
    evaluationAdditions,
    failures,
    summary: {
      candidateRunDirs: candidateRunDirs.length,
      loadedCount,
      skippedSameContent,
      skippedPredictRuns,
      skippedMissingJob,
      skippedUnsupportedVersion,
      skippedInvalid,
      skippedMissingPredictionId,
      skippedConflictingPredictionId,
    },
  };
}
