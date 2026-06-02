/**
 * Imported eval-dashboard run normalization helpers.
 */

import { omitTopLevelKeys } from "../utils/flatten.js";
import { normalizeValue } from "../utils/values.js";

/**
 * Create the named error used when an imported run uses an unsupported payload version.
 *
 * @param {unknown} version - The unsupported top-level version value.
 * @returns {Error & {name: string, jobReturnValueVersion: unknown}} Named unsupported-version error.
 */
export function createUnsupportedJobReturnValueVersionError(version) {
  const error = new Error(`Unsupported job_return_value.json version: ${version}`);
  error.name = "UnsupportedJobReturnValueVersionError";
  error.jobReturnValueVersion = version;
  return error;
}

/**
 * Normalize the embedded prediction payload into the dashboard's canonical shape.
 *
 * @param {Record<string, unknown>} job_return_value - Raw imported job-return payload.
 * @returns {{jobReturnValue: Record<string, unknown>, overrides: Record<string, unknown>}} Canonical prediction payload.
 */
export function getNormalizedPredictionFromJobReturnValue(job_return_value) {
  const prediction =
    job_return_value?.prediction &&
    typeof job_return_value.prediction === "object" &&
    !Array.isArray(job_return_value.prediction)
      ? job_return_value.prediction
      : {};
  return {
    jobReturnValue:
      prediction.job_return_value &&
      typeof prediction.job_return_value === "object" &&
      !Array.isArray(prediction.job_return_value)
        ? prediction.job_return_value
        : {},
    overrides:
      prediction.overrides &&
      typeof prediction.overrides === "object" &&
      !Array.isArray(prediction.overrides)
        ? prediction.overrides
        : {},
  };
}

/**
 * Create the named error used when a normalized prediction lacks its canonical id source.
 *
 * @returns {Error & {name: string}} Named missing-prediction-id error.
 */
export function createMissingPredictionIdError() {
  const error = new Error('job_return_value.json prediction.job_return_value.output_file must be present.');
  error.name = "MissingPredictionIdError";
  return error;
}

/**
 * Extract the canonical prediction id from a normalized prediction payload.
 *
 * @param {{jobReturnValue?: {output_file?: unknown}}} prediction - Normalized prediction payload.
 * @returns {string} Canonical prediction id.
 * @throws {Error} If the prediction id source is missing after normalization.
 */
export function getPredictionIdFromNormalizedPrediction(prediction) {
  const predictionId = normalizeValue(prediction?.jobReturnValue?.output_file).trim();
  if (!predictionId) {
    throw createMissingPredictionIdError();
  }
  return predictionId;
}

/**
 * Infer the legacy metric type for version-0/1 evaluation payloads from the override name.
 *
 * @param {unknown} activeExperiment - The `experiment/evaluate` override value.
 * @returns {string} Inferred metric type.
 */
export function getMetricTypeForExperiment(activeExperiment) {
  if (/confusion_matrix/i.test(activeExperiment || "")) {
    return "ConfusionMatrix";
  }
  if (/error/i.test(activeExperiment || "")) {
    return "ErrorCollector";
  }
  if (/tpfpfn/i.test(activeExperiment || "")) {
    return "TpFpFnCollector";
  }
  if (/f1_micro/i.test(activeExperiment || "")) {
    return "F1MicroMultipleFieldsMetric";
  }
  return "unknown";
}

const JOB_RETURN_VALUE_VERSION_HANDLERS = {
  0: (job_return_value, overrides) => ({
    prediction: getNormalizedPredictionFromJobReturnValue(job_return_value),
    evaluation: {
      jobReturnValue: {
        version: 0,
        type: getMetricTypeForExperiment(overrides?.["experiment/evaluate"]),
      },
      overrides: overrides || {},
      data: omitTopLevelKeys(job_return_value, new Set(["prediction"])),
    },
  }),
  1: (job_return_value, overrides) => ({
    prediction: getNormalizedPredictionFromJobReturnValue(job_return_value),
    evaluation: {
      jobReturnValue: {
        version: 1,
        type: getMetricTypeForExperiment(overrides?.["experiment/evaluate"]),
      },
      overrides: overrides || {},
      data: omitTopLevelKeys(job_return_value, new Set(["prediction", "version"])),
    },
  }),
  2: (job_return_value, overrides) => {
    if (!Object.prototype.hasOwnProperty.call(job_return_value, "data")) {
      throw new Error('job_return_value.json version 2 must contain a top-level "data" field.');
    }

    return {
      prediction: getNormalizedPredictionFromJobReturnValue(job_return_value),
      evaluation: {
        jobReturnValue: omitTopLevelKeys(job_return_value, new Set(["data", "prediction"])),
        overrides: overrides || {},
        data: job_return_value.data,
      },
    };
  },
};

/**
 * Normalize one imported `job_return_value.json` payload into the dashboard's canonical run shape.
 *
 * @param {unknown} job_return_value - Raw imported JSON payload.
 * @param {Record<string, string>} [overrides={}] - Parsed evaluation overrides.
 * @returns {{prediction: {jobReturnValue: Record<string, unknown>, overrides: Record<string, unknown>}, evaluation: {jobReturnValue: Record<string, unknown>, overrides: Record<string, string>, data: unknown}}} Canonical normalized run.
 * @throws {Error} If the payload is invalid or uses an unsupported version.
 */
export function normalizeImportedJobReturnValue(job_return_value, overrides = {}) {
  if (!job_return_value || typeof job_return_value !== "object" || Array.isArray(job_return_value)) {
    throw new Error("job_return_value.json must contain a top-level object.");
  }

  const version = Object.prototype.hasOwnProperty.call(job_return_value, "version")
    ? job_return_value.version
    : 0;
  const handler = JOB_RETURN_VALUE_VERSION_HANDLERS[version];

  if (!handler) {
    throw createUnsupportedJobReturnValueVersionError(version);
  }

  const normalized = handler(job_return_value, overrides);
  if (
    !normalized ||
    typeof normalized !== "object" ||
    !normalized.prediction ||
    typeof normalized.prediction !== "object" ||
    !normalized.evaluation ||
    typeof normalized.evaluation !== "object"
  ) {
    throw new Error(`job_return_value.json version ${version} normalization returned an invalid shape.`);
  }
  return normalized;
}
