/**
 * Run-identity helpers shared across eval-dashboard ingestion, state, and plots.
 */

import { flattenObject } from "./flatten.js";
import { getStableObjectSignature, normalizeValue } from "./values.js";

/**
 * Resolve the canonical semantic run id for one evaluation-like record.
 *
 * Newer evaluation records carry a content-derived `runId`. Older state may
 * still only have `runDir`, so this helper keeps semantic callers compatible
 * while the state model migrates.
 *
 * @param {object | null | undefined} evaluation - Evaluation or collection-view record.
 * @returns {string} Canonical run id, or an empty string when unavailable.
 */
export function getEvaluationRunId(evaluation) {
  const runId = normalizeValue(evaluation?.runId).trim();
  if (runId) {
    return runId;
  }
  return normalizeValue(evaluation?.runDir).trim();
}

/**
 * Build the stable content signature for one imported evaluation run.
 *
 * The source of truth is the parsed `job_return_value.json` payload together
 * with the parsed `.hydra/overrides.yaml` content. Flattening both inputs keeps
 * the signature insensitive to nested object key ordering while preserving all
 * semantic values.
 *
 * @param {Record<string, unknown>} jobReturnValue - Parsed job-return payload.
 * @param {Record<string, unknown>} overrides - Parsed overrides payload.
 * @returns {string} Stable canonical content signature.
 */
export function getRunContentSignature(jobReturnValue, overrides) {
  return getStableObjectSignature({
    ...flattenObject(jobReturnValue || {}, "job_return_value"),
    ...flattenObject(overrides || {}, "overrides"),
  });
}

/**
 * Derive the canonical content-based run id for one imported evaluation run.
 *
 * The id is the SHA-256 hash of the stable signature produced from the parsed
 * source files. This keeps semantic identity independent from import path or
 * formatting-only differences in the source files.
 *
 * @param {Record<string, unknown>} jobReturnValue - Parsed job-return payload.
 * @param {Record<string, unknown>} overrides - Parsed overrides payload.
 * @param {object} [options] - Optional crypto and encoding overrides for tests.
 * @param {{subtle?: {digest?: (algorithm: string, data: Uint8Array) => Promise<ArrayBuffer>}}} [options.cryptoLike=globalThis.crypto] - Crypto-like dependency.
 * @param {typeof TextEncoder} [options.TextEncoderLike=globalThis.TextEncoder] - TextEncoder constructor override.
 * @returns {Promise<string>} Hex-encoded SHA-256 run id.
 * @throws {Error} If Web Crypto or TextEncoder is unavailable.
 */
export async function getRunIdFromImportedSources(
  jobReturnValue,
  overrides,
  {
    cryptoLike = globalThis.crypto,
    TextEncoderLike = globalThis.TextEncoder,
  } = {}
) {
  if (typeof TextEncoderLike !== "function") {
    throw new Error("Run-id hashing requires TextEncoder support.");
  }
  if (typeof cryptoLike?.subtle?.digest !== "function") {
    throw new Error("Run-id hashing requires Web Crypto digest support.");
  }

  const signature = getRunContentSignature(jobReturnValue, overrides);
  const encoded = new TextEncoderLike().encode(signature);
  const digest = await cryptoLike.subtle.digest("SHA-256", encoded);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

