/**
 * Tests for shared eval-dashboard plot helper seams.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildGroupedLegendModel,
  getLegendItemsForPoints,
  getPlotDisplayLabel,
  getVaryingFields,
  fitSvgToContents,
  scheduleAdaptiveSvgFit,
  styleErrorBarSegment,
} from "../../../../docs/eval-dashboard/assets/js/plots/shared.js";
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
 * Verify shortened plot labels and grouped-series legend models.
 */
test("shared plot helpers derive labels and legend models", () => {
  assert.equal(getPlotDisplayLabel("a.b.c", { shortenLabels: true }), "c");

  const legend = buildGroupedLegendModel([
    {
      points: [
        { series: "s1", displaySeries: "Series 1" },
        { series: "s2", displaySeries: "Series 2" },
      ],
    },
  ]);
  assert.deepEqual(legend.items.map((item) => item.label), ["Series 1", "Series 2"]);
  assert.deepEqual(getLegendItemsForPoints([{ series: "s2" }], legend).map((item) => item.series), ["s2"]);
});

/**
 * Verify shared SVG helpers style error bars and fit connected SVG content.
 */
test("shared plot helpers style and adapt SVG dimensions", () => {
  const documentLike = createDocumentStub();
  const svg = documentLike.createElementNS("", "svg");
  const group = documentLike.createElementNS("", "g");
  group._bbox = { x: -12, y: -5, width: 140.2, height: 80.1 };
  svg.appendChild(group);

  const line = documentLike.createElementNS("", "line");
  styleErrorBarSegment(line);
  assert.equal(line.getAttribute("stroke"), "currentColor");
  assert.equal(line.getAttribute("stroke-opacity"), "0.78");

  assert.equal(fitSvgToContents(svg, group, 100, 60), true);
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
