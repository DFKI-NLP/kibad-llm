/**
 * Browser-free logic tests for the eval-dashboard run-identity utilities.
 */

import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import test from "node:test";

import {
  getEvaluationRunId,
  getRunContentSignature,
  getRunIdFromImportedSources,
} from "../../../../docs/eval-dashboard/assets/js/utils/runs.js";

/**
 * Ensure semantic identity uses only the normalized run id and never falls back to source paths.
 */
test("run helpers normalize evaluation ids without using runDir as a fallback", () => {
  assert.equal(getEvaluationRunId({ runId: "  run-123  ", runDir: "logs/run-a" }), "run-123");
  assert.equal(getEvaluationRunId({ runId: 42, runDir: "logs/run-a" }), "42");
  assert.equal(getEvaluationRunId({ runDir: "logs/run-a" }), "");
  assert.equal(getEvaluationRunId({ runId: "   ", runDir: "logs/run-a" }), "");
  assert.equal(getEvaluationRunId(null), "");
  assert.equal(getEvaluationRunId(undefined), "");
});

/**
 * Ensure source signatures include both parsed inputs while remaining stable across object key order.
 */
test("run content signatures are stable and distinguish semantic changes", () => {
  const signatureA = getRunContentSignature(
    { model: "demo", nested: { beta: 2, alpha: 1 } },
    { seed: "7", temperature: "0" }
  );
  const signatureB = getRunContentSignature(
    { nested: { alpha: 1, beta: 2 }, model: "demo" },
    { temperature: "0", seed: "7" }
  );

  assert.equal(signatureA, signatureB);
  assert.notEqual(
    signatureA,
    getRunContentSignature(
      { model: "demo", nested: { beta: 3, alpha: 1 } },
      { seed: "7", temperature: "0" }
    )
  );
  assert.notEqual(
    signatureA,
    getRunContentSignature(
      { model: "demo", nested: { beta: 2, alpha: 1 } },
      { seed: "8", temperature: "0" }
    )
  );
  assert.equal(getRunContentSignature(null, undefined), "{}");
});

/**
 * Ensure hashing uses SHA-256 and returns the expected lower-case hexadecimal digest.
 */
test("run id hashing derives a deterministic SHA-256 id from parsed sources", async () => {
  const jobReturnValue = { model: "demo", seed: 7 };
  const overrides = { experiment: "evaluate" };
  const firstId = await getRunIdFromImportedSources(jobReturnValue, overrides, {
    cryptoLike: webcrypto,
    TextEncoderLike: TextEncoder,
  });
  const secondId = await getRunIdFromImportedSources(
    { seed: 7, model: "demo" },
    { experiment: "evaluate" },
    { cryptoLike: webcrypto, TextEncoderLike: TextEncoder }
  );

  assert.equal(firstId, secondId);
  assert.match(firstId, /^[a-f0-9]{64}$/);
});

/**
 * Ensure the hashing pipeline passes the canonical signature and algorithm to injected dependencies.
 */
test("run id hashing supports injected encoder and digest dependencies", async () => {
  let encodedSignature = null;
  let digestAlgorithm = null;
  class TestEncoder {
    constructor() {
      this.encode = (value) => {
        encodedSignature = value;
        return new Uint8Array([1, 2, 3]);
      };
    }
  }
  const cryptoLike = {
    subtle: {
      digest: async (algorithm, data) => {
        digestAlgorithm = algorithm;
        assert.deepEqual(Array.from(data), [1, 2, 3]);
        return Uint8Array.from([0, 1, 15, 16, 255]).buffer;
      },
    },
  };
  assert.equal(typeof cryptoLike.subtle.digest, "function");

  const jobReturnValue = { answer: 42 };
  const overrides = { seed: "1" };
  const runId = await getRunIdFromImportedSources(jobReturnValue, overrides, {
    cryptoLike,
    TextEncoderLike: TestEncoder,
  });

  assert.equal(encodedSignature, getRunContentSignature(jobReturnValue, overrides));
  assert.equal(digestAlgorithm, "SHA-256");
  assert.equal(runId, "00010f10ff");
});

/**
 * Ensure unsupported browser capabilities fail clearly before attempting to hash input.
 */
test("run id hashing reports missing TextEncoder and Web Crypto support", async () => {
  await assert.rejects(
    getRunIdFromImportedSources({}, {}, { TextEncoderLike: null, cryptoLike: webcrypto }),
    /requires TextEncoder support/
  );
  await assert.rejects(
    getRunIdFromImportedSources({}, {}, { TextEncoderLike: TextEncoder, cryptoLike: {} }),
    /requires Web Crypto digest support/
  );
});

