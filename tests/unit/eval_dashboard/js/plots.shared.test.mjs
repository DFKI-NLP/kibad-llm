/**
 * Tests for shared eval-dashboard plot helper seams.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  getPlotDisplayLabel,
  getVaryingFields,
  scheduleAdaptiveSvgFit,
} from "../../../../docs/eval-dashboard/assets/js/plots/shared.js";
import {
  buildMatrixDownloadMetadata,
} from "../../../../docs/eval-dashboard/assets/js/plots/shared-matrix.js";
import { createDocumentStub } from "./plots.dom-test-helpers.mjs";

/**
 * Verify shared grouping helpers detect varying fields.
 */
test("shared plot helpers detect varying group fields", () => {
  const plotGroups = [
    {
      values: { model: "a", seed: "1" },
    },
    {
      values: { model: "b", seed: "1" },
    },
  ];

  assert.deepEqual(getVaryingFields(plotGroups, ["model", "seed"]), ["model"]);
});

/**
 * Verify shortened plot labels.
 */
test("shared plot helpers derive display labels", () => {
  assert.equal(getPlotDisplayLabel("a.b.c", { shortenLabels: true }), "c");
});

/**
 * Verify matrix download metadata uses an explicit public-field allowlist.
 */
test("shared matrix helpers build download metadata", () => {
  assert.deepEqual(
    buildMatrixDownloadMetadata({
      label: "model=a",
      fieldLabel: "field_a",
      collections: [{ fields: new Map() }],
      internalField: "must not leak",
    }),
    {
      label: "model=a",
      fieldLabel: "field_a",
    }
  );
});

/**
 * Verify shared SVG helpers adapt connected SVG content.
 */
test("shared plot helpers adapt SVG dimensions", async () => {
  const documentLike = createDocumentStub();
  const svg = documentLike.createElementNS("", "svg");
  const group = documentLike.createElementNS("", "g");
  group._bbox = { x: -12, y: -5, width: 140.2, height: 80.1 };
  svg.appendChild(group);

  scheduleAdaptiveSvgFit({
    documentLike: {},
    requestAnimationFrameLike: (callback) => callback(),
    svg,
    contentGroup: group,
    minWidth: 100,
    minHeight: 60,
  });
  assert.equal(group.getAttribute("transform"), "translate(20, 13)");
  assert.equal(svg.getAttribute("viewBox"), "0 0 157 97");
});

/**
 * Verify adaptive SVG fitting retries disconnected content and refits after fonts load.
 */
test("shared plot helpers schedule adaptive SVG fitting retries", async () => {
  let resolveFonts;
  const documentLike = {
    fonts: {
      ready: new Promise((resolve) => {
        resolveFonts = resolve;
      }),
    },
  };
  const svg = { isConnected: false, setAttribute: () => {} };
  const group = { getBBox: () => ({ x: 0, y: 0, width: 10, height: 10 }), setAttribute: () => {} };
  let frames = 0;

  scheduleAdaptiveSvgFit({
    documentLike,
    requestAnimationFrameLike: (callback) => {
      frames += 1;
      callback();
    },
    svg,
    contentGroup: group,
    minWidth: 20,
    minHeight: 20,
  });
  assert.equal(frames, 5);

  svg.isConnected = true;
  resolveFonts();
  await documentLike.fonts.ready;
  await Promise.resolve();
  assert.equal(frames, 6);
});
