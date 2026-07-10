/**
 * Tests for eval-dashboard TP/FP/FN plot helper seams.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildTpFpFnCellClipboardPayload,
  buildTpFpFnCellDetails,
  buildTpFpFnCellTooltipLines,
  buildTpFpFnTabMap,
  createTpFpFnCombinedMatrixSvg,
  createTpFpFnLegendElement,
  filterTpFpFnAggregationByTotals,
  getTpFpFnAggregationInput,
  getTpFpFnAggregationFromInput,
  getTpFpFnCollectionViews,
  getTpFpFnOutcomeColor,
  normalizeTpFpFnCollectorData,
} from "../../../../docs/eval-dashboard/assets/js/plots/tpfpfn.js";
import { createDocumentStub } from "./plots.dom-test-helpers.mjs";

const getEvaluationEffectiveValue = (evaluation, column) =>
  evaluation.overrides?.[column] ?? "";

const aggregateTpFpFn = (collections, fieldLabel) =>
  getTpFpFnAggregationFromInput(
    getTpFpFnAggregationInput(collections, fieldLabel)
  );

/**
 * Verify both TP/FP/FN input shapes normalize into stable per-record buckets.
 */
test("tpfpfn helpers normalize collector data and aggregate outcomes", () => {
  assert.deepEqual(
    normalizeTpFpFnCollectorData({
      doc2: { tp: ["B"], fp: ["A"], fn: [] },
      doc1: { tp: ["A", "A"], fp: [], fn: ["C"] },
    }),
    {
      doc1: { tp: ["A"], fp: [], fn: ["C"] },
      doc2: { tp: ["B"], fp: ["A"], fn: [] },
    }
  );

  assert.deepEqual(
    normalizeTpFpFnCollectorData({
      tp: [["doc1", "A"]],
      fp: [["doc2", "B"]],
      fn: [["doc1", "C"]],
    }),
    {
      doc1: { tp: ["A"], fp: [], fn: ["C"] },
      doc2: { tp: [], fp: ["B"], fn: [] },
    }
  );

  const aggregation = aggregateTpFpFn([
    { runId: "r1-id", runDir: "r1", fields: new Map([["field_a", { doc1: { tp: ["A"], fp: [], fn: ["B"] } }]]) },
    { runId: "r2-id", runDir: "r2", fields: new Map([["field_a", { doc1: { tp: [], fp: ["A"], fn: [] }, doc2: { tp: ["C"], fp: [], fn: [] } }]]) },
  ], "field_a");
  assert.deepEqual(aggregation.rows, ["doc1", "doc2"]);
  assert.deepEqual(aggregation.cols, ["A", "B", "C"]);
  assert.deepEqual(aggregation.cells.get("doc1|#|A").counts, { tp: 1, fp: 1, fn: 0, empty: 0 });
  assert.deepEqual(aggregation.cells.get("doc2|#|C").counts, { tp: 1, fp: 0, fn: 0, empty: 1 });

  const filtered = filterTpFpFnAggregationByTotals(aggregation, 2, 1);
  assert.deepEqual(filtered.rows, ["doc1"]);
  assert.deepEqual(filtered.cols, ["A"]);
});

/**
 * Verify TP/FP/FN aggregation caches prepared per-evaluation field data lazily.
 */
test("tpfpfn aggregation stores prepared field data on the source evaluation", () => {
  const evaluation = {
    runId: "r1-id",
    runDir: "r1",
    jobReturnValue: { type: "TpFpFnCollectorCollection" },
    data: { field_a: { doc: { tp: ["A"], fp: [], fn: [] } } },
  };
  const [collection] = getTpFpFnCollectionViews([evaluation]);

  const aggregation = aggregateTpFpFn([collection], "field_a");

  assert.deepEqual(aggregation.cells.get("doc|#|A").counts, { tp: 1, fp: 0, fn: 0, empty: 0 });
  assert.ok(evaluation.dataPrepared.field_a);
  assert.deepEqual(Object.keys(evaluation), ["runId", "runDir", "jobReturnValue", "data"]);
  assert.equal(evaluation.dataPrepared.field_a.cells.get("doc|#|A"), "tp");
});

/**
 * Verify cache lookup handles metric fields that collide with object prototype names.
 */
test("tpfpfn aggregation caches prototype-named metric fields safely", () => {
  const evaluation = {
    runId: "r1-id",
    runDir: "r1",
    jobReturnValue: { type: "TpFpFnCollectorCollection" },
    data: { toString: { doc: { tp: ["A"], fp: [], fn: [] } } },
  };
  const [collection] = getTpFpFnCollectionViews([evaluation]);

  const aggregation = aggregateTpFpFn([collection], "toString");

  assert.deepEqual(aggregation.cells.get("doc|#|A").counts, { tp: 1, fp: 0, fn: 0, empty: 0 });
  assert.equal(evaluation.dataPrepared.toString.cells.get("doc|#|A"), "tp");
});

/**
 * Verify existing plain prepared-data containers are normalized before caching.
 */
test("tpfpfn aggregation normalizes existing prepared containers for prototype keys", () => {
  const data = {};
  Object.defineProperty(data, "__proto__", {
    value: { doc: { tp: ["A"], fp: [], fn: [] } },
    enumerable: true,
    configurable: true,
  });
  const evaluation = {
    runId: "r1-id",
    runDir: "r1",
    jobReturnValue: { type: "TpFpFnCollectorCollection" },
    dataPrepared: {},
    data,
  };
  const [collection] = getTpFpFnCollectionViews([evaluation]);

  const aggregation = aggregateTpFpFn([collection], "__proto__");

  assert.deepEqual(aggregation.cells.get("doc|#|A").counts, { tp: 1, fp: 0, fn: 0, empty: 0 });
  assert.equal(Object.getPrototypeOf(evaluation.dataPrepared), null);
  assert.equal(evaluation.dataPrepared.__proto__.cells.get("doc|#|A"), "tp");
});

/**
 * Verify TP/FP/FN aggregation exposes reusable aligned inputs.
 */
test("tpfpfn helpers build reusable aligned aggregation inputs", () => {
  const collections = [
    {
      runId: "run-a-id",
      runDir: "run-a",
      sourceRunDir: "source-a",
      fields: new Map([["field_a", { doc1: { tp: ["A"], fp: ["B"], fn: [] }, filtered: { fn: ["hidden"] } }]]),
    },
    {
      runId: "run-b-id",
      runDir: "run-b",
      sourceRunDir: "source-b",
      fields: new Map([["field_a", { doc1: { tp: [], fp: [], fn: ["A"] } }]]),
    },
  ];
  const input = getTpFpFnAggregationInput(collections, "field_a");
  const aggregation = getTpFpFnAggregationFromInput(input);

  assert.deepEqual(input.rows, ["doc1", "filtered"]);
  assert.deepEqual(input.cols, ["A", "B", "hidden"]);
  assert.deepEqual(input.runDirs, ["source-a", "source-b"]);
  assert.equal(input.cells[0].get("doc1|#|A"), "tp");
  assert.equal(input.cells[1].get("doc1|#|A"), "fn");
  assert.deepEqual(aggregation.cells.get("doc1|#|A").counts, { tp: 1, fp: 0, fn: 1, empty: 0 });
  assert.equal("outcomes" in aggregation.cells.get("doc1|#|A"), false);
  assert.deepEqual(aggregation.cells.get("filtered|#|hidden").counts, { tp: 0, fp: 0, fn: 1, empty: 1 });
  assert.equal("runDirs" in aggregation, false);

  assert.throws(
    () => getTpFpFnAggregationFromInput({
      rows: [],
      cols: [],
      runDirs: ["source-a"],
      cells: [],
    }),
    /runDirs\.length \(1\) to equal cells\.length \(0\)/
  );
});

/**
 * Verify TP/FP/FN collection views, tab grouping, cell summaries, and palette output.
 */
test("tpfpfn helpers wrap collection metrics, build tab maps, and summarize cells", () => {
  const collectionData = {
    "outer.field_a": { doc: { tp: ["A"] } },
    "outer.field_b": { doc: { fp: ["B"] } },
  };
  const collections = getTpFpFnCollectionViews([
    {
      runId: "run-a-id",
      runDir: "run-a",
      jobReturnValue: { type: "TpFpFnCollectorCollection" },
      data: collectionData,
    },
  ]);
  assert.equal(collections.length, 1);
  assert.deepEqual(Array.from(collections[0].fields.keys()), ["outer.field_a", "outer.field_b"]);
  assert.equal(collections[0].fields.get("outer.field_a"), collectionData["outer.field_a"]);

  const evaluations = [{
    runId: "run-a-id",
    runDir: "run-a",
    jobReturnValue: { type: "TpFpFnCollectorCollection" },
    overrides: { experiment: "exp" },
    data: collectionData,
  }];
  const tabMap = buildTpFpFnTabMap({
    plotGroups: [{ groupId: "g1", values: { model: "a" }, evaluations }],
    labelFields: ["model"],
    evalTabState: {},
    matrixTabsBy: "metric_field",
    getEvaluationEffectiveValue,
    displayPlotGroupFieldName: (field) => field,
    shortenLabels: true,
  });
  assert.deepEqual(Array.from(tabMap.keys()), ["outer.field_a", "outer.field_b"]);
  assert.deepEqual(Array.from(tabMap.values()).map((entry) => entry.label), ["field_a", "field_b"]);
  assert.equal(tabMap.get("outer.field_a").plots[0].collections[0].fields.get("outer.field_a"), collectionData["outer.field_a"]);

  const details = buildTpFpFnCellDetails(
    {
      counts: { tp: 1, fp: 1, fn: 0, empty: 1 },
    },
    3
  );
  assert.deepEqual(details.shares, { tp: 1 / 3, fp: 1 / 3, fn: 0 });
  assert.equal("values" in details, false);
  assert.equal("runDirs" in details, false);
  assert.deepEqual(
    buildTpFpFnCellTooltipLines("doc", "A", details, 2),
    ["document: doc", "label:    A", "TP/FP/FN %: 33.33 / 33.33 / 0.00"]
  );
  const cells = [
    new Map([["doc|#|A", "tp"]]),
    new Map([["doc|#|A", "fp"]]),
    new Map(),
  ];
  const payload = buildTpFpFnCellClipboardPayload(
    "doc",
    "A",
    details,
    cells,
    ["r1", "r2", "r3"]
  );
  assert.ok(Math.abs(payload.percentages.tp - (100 / 3)) < Number.EPSILON * 100);
  assert.deepEqual(payload.values, ["tp", "fp", "empty"]);
  assert.deepEqual(payload.run_dirs, ["r1", "r2", "r3"]);
  assert.throws(
    () => buildTpFpFnCellClipboardPayload(
      "doc",
      "A",
      details,
      [new Map([["doc|#|A", "tp"]])],
      []
    ),
    /TpFpFnCollector clipboard payload requires runDirs\.length \(0\) to equal cells\.length \(1\)/
  );
  assert.equal(getTpFpFnOutcomeColor("tp"), "rgb(22, 163, 74)");
});

/**
 * Verify malformed TP/FP/FN metric records fail at the adapter boundary.
 */
test("tpfpfn collection views reject missing fields and malformed collection data", () => {
  assert.throws(
    () => getTpFpFnCollectionViews([
      { runId: "r1-id", runDir: "r1", overrides: {}, jobReturnValue: { type: "TpFpFnCollector" }, data: {} },
    ], { evalTabState: {}, getEvaluationEffectiveValue }),
    /TpFpFnCollector evaluation must define a non-empty metric\.field\./
  );

  assert.throws(
    () => getTpFpFnCollectionViews([
      { runId: "r1-id", runDir: "r1", jobReturnValue: { type: "TpFpFnCollectorCollection" }, data: [] },
    ]),
    /TpFpFnCollectorCollection data must be an object mapping metric fields to metric data\./
  );

  assert.throws(
    () => getTpFpFnCollectionViews([
      {
        runId: "r1-id",
        runDir: "r1",
        jobReturnValue: { type: "TpFpFnCollectorCollection" },
        data: { " field_a ": {}, field_a: {} },
      },
    ]),
    /TpFpFnCollectorCollection data contains duplicate metric field "field_a" after normalization\./
  );

  assert.throws(
    () => aggregateTpFpFn([
      { runId: "r1-id", runDir: "r1", fields: new Map([["field_b", {}]]) },
    ], "field_a"),
    /TpFpFnCollector collection view is missing metric field "field_a"\./
  );

  assert.throws(
    () => normalizeTpFpFnCollectorData(null),
    /TpFpFnCollector data must be an object\./
  );

  assert.throws(
    () => normalizeTpFpFnCollectorData({ tp: [["doc1"]] }),
    /TpFpFnCollector global bucket "tp" entry 0 must be a \[record_id, label] array\./
  );

  assert.throws(
    () => normalizeTpFpFnCollectorData({ tp: [["doc1", "label", "extra"]] }),
    /TpFpFnCollector global bucket "tp" entry 0 must be a \[record_id, label] array\./
  );

  assert.throws(
    () => normalizeTpFpFnCollectorData({ tp: [["", "label"]] }),
    /TpFpFnCollector data contains an empty record id\./
  );

  assert.throws(
    () => normalizeTpFpFnCollectorData({ doc1: [] }),
    /TpFpFnCollector record "doc1" must contain object bucket data\./
  );

  assert.throws(
    () => normalizeTpFpFnCollectorData({ doc1: { tp: "label" } }),
    /TpFpFnCollector record "doc1" bucket "tp" must be an array\./
  );

  assert.throws(
    () => normalizeTpFpFnCollectorData({ doc1: { tp: [""] } }),
    /TpFpFnCollector record "doc1" bucket "tp" contains an empty label at index 0\./
  );

  assert.throws(
    () => aggregateTpFpFn([
      {
        runId: "r1-id",
        runDir: "r1",
        fields: new Map([[
          "field_a",
          { doc1: { tp: ["label"], fp: ["label"], fn: [] } },
        ]]),
      },
    ], "field_a"),
    /record "doc1" label "label" cannot be both "tp" and "fp"/
  );

  assert.throws(
    () => aggregateTpFpFn([
      {
        runId: "r1-id",
        runDir: "r1",
        fields: new Map([[
          "field_a",
          {
            "a|#|b": { tp: ["c"] },
            a: { fp: ["b|#|c"] },
          },
        ]]),
      },
    ], "field_a"),
    /record id "a\|#\|b" must not contain reserved matrix key delimiter "\|#\|"/
  );
});

/**
 * Verify TP/FP/FN legend rendering uses the outcome labels and colors.
 */
test("tpfpfn renderer creates outcome legend elements", () => {
  const documentLike = createDocumentStub();
  const legend = createTpFpFnLegendElement({ documentLike });

  assert.equal(legend.className, "plot-legend");
  assert.deepEqual(legend.querySelectorAll(".plot-legend-item").map((item) => item.children[1].textContent), ["TP", "FP", "FN"]);
  assert.equal(legend.querySelectorAll(".plot-legend-swatch")[0].style.backgroundColor, "rgb(22, 163, 74)");
});

/**
 * Verify TP/FP/FN matrix SVG rendering exposes labels, tooltips, and successful clipboard copies.
 */
test("tpfpfn renderer creates interactive combined matrix cells", async () => {
  const documentLike = createDocumentStub();
  const shown = [];
  let copied = "";
  const aggregationInput = getTpFpFnAggregationInput([
    { runId: "r1-id", runDir: "r1", fields: new Map([["field_a", { doc1: { tp: ["outer.label"], fp: [], fn: [] } }]]) },
    { runId: "r2-id", runDir: "r2", fields: new Map([["field_a", { doc1: { tp: [], fp: ["outer.label"], fn: [] } }]]) },
  ], "field_a");
  const aggregation = getTpFpFnAggregationFromInput(aggregationInput);

  const svg = createTpFpFnCombinedMatrixSvg({
    documentLike,
    requestAnimationFrameLike: (callback) => callback(),
    aggregation,
    aggregationInput,
    precision: 1,
    getDisplayLabel: (label) => label.split(".").at(-1),
    showTooltip: (_event, lines) => shown.push(lines),
    moveTooltip: () => {},
    hideTooltip: () => {},
    writeTextToClipboard: async (text) => {
      copied = text;
    },
  });

  assert.ok(svg.querySelectorAll("text").some((text) => text.textContent === "label"));
  const overlay = svg.querySelectorAll("rect").find((rect) => rect.getAttribute("fill") === "transparent");
  overlay.dispatch("mouseover", { clientX: 10, clientY: 10 });
  assert.deepEqual(shown[0], ["document: doc1", "label:    outer.label", "TP/FP/FN %: 50.0 / 50.0 / 0.0"]);

  await overlay.dispatch("click", { clientX: 10, clientY: 10 });
  assert.deepEqual(JSON.parse(copied).values, ["tp", "fp"]);
  assert.deepEqual(JSON.parse(copied).run_dirs, ["r1", "r2"]);
  assert.equal(shown.at(-1).at(-1), "Copied JSON to clipboard.");
});

/**
 * Verify TP/FP/FN matrix click handling reports clipboard failures without throwing.
 */
test("tpfpfn renderer reports clipboard copy failures", async () => {
  const documentLike = createDocumentStub();
  const shown = [];
  const warnings = [];
  const aggregationInput = getTpFpFnAggregationInput([
    { runId: "r1-id", runDir: "r1", fields: new Map([["field_a", { doc1: { tp: ["label"], fp: [], fn: [] } }]]) },
  ], "field_a");
  const aggregation = getTpFpFnAggregationFromInput(aggregationInput);
  const svg = createTpFpFnCombinedMatrixSvg({
    documentLike,
    requestAnimationFrameLike: (callback) => callback(),
    aggregation,
    aggregationInput,
    precision: 2,
    showTooltip: (_event, lines) => shown.push(lines),
    moveTooltip: () => {},
    hideTooltip: () => {},
    writeTextToClipboard: async () => {
      throw new Error("no clipboard");
    },
    consoleLike: { warn: (...args) => warnings.push(args) },
  });

  const overlay = svg.querySelectorAll("rect").find((rect) => rect.getAttribute("fill") === "transparent");
  await overlay.dispatch("click", { clientX: 10, clientY: 10 });
  assert.equal(shown.at(-1).at(-1), "Copy to clipboard failed.");
  assert.equal(warnings.length, 1);
});
