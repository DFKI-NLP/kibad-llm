/**
 * Tests for eval-dashboard plot legend helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildGroupedLegendModel,
  createPlotLegendElement,
  getLegendItemsForPoints,
} from "../../../../docs/eval-dashboard/assets/js/plots/legend.js";
import { createDocumentStub } from "./plots.dom-test-helpers.mjs";

/**
 * Verify grouped-series legend models preserve stable order, labels, and colors.
 */
test("legend helpers derive grouped legend models", () => {
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
 * Verify the shared legend DOM renderer creates swatches and labels.
 */
test("legend helpers render plot legend elements", () => {
  const documentLike = createDocumentStub();
  const legend = createPlotLegendElement({
    documentLike,
    legendItems: [{ label: "Series", color: "#ff0000" }],
  });

  assert.equal(legend.className, "plot-legend");
  assert.equal(legend.querySelector(".plot-legend-swatch").style.backgroundColor, "#ff0000");
  assert.equal(legend.querySelector(".plot-legend-item").children[1].textContent, "Series");
});
