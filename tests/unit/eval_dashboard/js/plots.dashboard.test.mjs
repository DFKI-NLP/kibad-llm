/**
 * Tests for the eval-dashboard plot-surface adapter.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  createPlotTooltipHandlers,
  downloadVisiblePlotFigures,
  renderDashboardPlotControls,
  renderEvaluationPlotsForDashboard,
  resolvePlotExportBackgroundColor,
  updateDownloadDataButtonState,
  updateDownloadFiguresButtonState,
} from "../../../../docs/eval-dashboard/assets/js/plots/dashboard.js";
import {
  buildJsonSafeActivePlotDownloadData,
  downloadActivePlotData,
} from "../../../../docs/eval-dashboard/assets/js/plots/download-data.js";
import { createDocumentStub, serializeFakeSvg } from "./plots.dom-test-helpers.mjs";

function createPlotDom(documentLike) {
  return {
    evalPlotTabs: documentLike.createElement("div"),
    evalPlotContent: documentLike.createElement("div"),
    plotGroupBarsList: documentLike.createElement("div"),
    plotTabsByPrefixButton: documentLike.createElement("button"),
    plotTabsBySuffixButton: documentLike.createElement("button"),
    confusionTabsByMetricFieldButton: documentLike.createElement("button"),
    confusionTabsByPredictionGroupButton: documentLike.createElement("button"),
    plotShortenLabels: documentLike.createElement("input"),
    plotRoundingPrecision: documentLike.createElement("input"),
    plotConfusionMinLabelTotalRow: documentLike.createElement("div"),
    plotConfusionMinLabelTotal: documentLike.createElement("input"),
    plotTpFpFnMinLabelTotalRow: documentLike.createElement("div"),
    plotTpFpFnMinLabelTotal: documentLike.createElement("input"),
    plotTpFpFnMinDocumentTotalRow: documentLike.createElement("div"),
    plotTpFpFnMinDocumentTotal: documentLike.createElement("input"),
    plotTabsByRow: documentLike.createElement("div"),
    plotConfusionTabsByRow: documentLike.createElement("div"),
    plotGroupBarsRow: documentLike.createElement("div"),
    plotShowLegendOnceRow: documentLike.createElement("div"),
    plotShowLegendOnce: documentLike.createElement("input"),
    exportOpaqueBackground: documentLike.createElement("input"),
  };
}

function createPlotState(overrides = {}) {
  return {
    activeEvalTab: "experiment/a",
    activeEvalPlotTab: null,
    activePlotDownloadData: null,
    activePlotLegendItems: [],
    plotTabsBy: "prefix",
    confusionTabsBy: "metric_field",
    plotShortenLabels: false,
    plotRoundingPrecision: 4,
    plotConfusionMinLabelTotal: 2,
    plotTpFpFnMinLabelTotal: 3,
    plotTpFpFnMinDocumentTotal: 0,
    plotShowLegendOnce: true,
    exportOpaqueBackground: false,
    plotGroupBarFields: new Set(),
    ...overrides,
  };
}

/**
 * Verify the dashboard adapter wires the shared tooltip helpers without changing positions.
 */
test("dashboard plot tooltip handlers show, move, and hide the shared tooltip", () => {
  const tooltipElement = { offsetWidth: 60, offsetHeight: 20, style: {}, textContent: "" };
  const handlers = createPlotTooltipHandlers({
    tooltipElement,
    windowLike: { innerWidth: 200 },
  });

  handlers.show({ clientX: 150, clientY: 10 }, ["score", "mean: 1"]);
  assert.equal(tooltipElement.textContent, "score\nmean: 1");
  assert.equal(tooltipElement.style.display, "block");
  assert.equal(tooltipElement.style.left, "76px");

  handlers.move({ clientX: 20, clientY: 100 });
  assert.equal(tooltipElement.style.left, "34px");
  assert.equal(tooltipElement.style.top, "66px");

  handlers.hide();
  assert.equal(tooltipElement.style.display, "none");
});

/**
 * Verify dashboard export state is resolved from the active plot DOM.
 */
test("dashboard export helpers sync button state and opaque background selection", () => {
  const documentLike = createDocumentStub();
  const evalPlotContent = documentLike.createElement("div");
  const card = documentLike.createElement("section");
  card.className = "plot-card";
  card.appendChild(documentLike.createElementNS("", "svg"));
  evalPlotContent.appendChild(card);

  const downloadFiguresButton = documentLike.createElement("button");
  updateDownloadFiguresButtonState({ downloadFiguresButton, evalPlotContent });
  assert.equal(downloadFiguresButton.disabled, false);
  assert.equal(downloadFiguresButton.textContent, "Download Figures (1)");

  assert.equal(
    resolvePlotExportBackgroundColor({
      evalPlotContent,
      documentLike,
      getStyle: (element) => ({
        backgroundColor: element === evalPlotContent ? "rgba(0, 0, 0, 0)" : "#f8f8f8",
      }),
    }),
    "#f8f8f8"
  );

  const downloadDataButton = documentLike.createElement("button");
  updateDownloadDataButtonState({ downloadDataButton, state: createPlotState() });
  assert.equal(downloadDataButton.disabled, true);
  assert.equal(downloadDataButton.textContent, "Download Data");
  updateDownloadDataButtonState({
    downloadDataButton,
    state: createPlotState({ activePlotDownloadData: { plots: [{ label: "one" }, { label: "two" }] } }),
  });
  assert.equal(downloadDataButton.disabled, false);
  assert.equal(downloadDataButton.textContent, "Download Data (2)");
});

/**
 * Verify the dashboard-level data download helper saves the active plot payload as JSON.
 */
test("dashboard data download helper exports active plot data as JSON", async () => {
  let saved = null;
  const payload = {
    metric_family: "numeric",
    plot_tab: "score",
    plots: [{
      metaData: { metricLabel: "score.mean" },
      dataSource: {
        points: [{
          category: "model=a",
          displayCategory: "Model A",
          series: "__single__",
          displaySeries: "__single__",
          samples: [0.75],
        }],
      },
    }],
  };
  const expectedJson = {
    metric_family: "numeric",
    plot_tab: "score",
    plots: [{
      metaData: { metricLabel: "score.mean" },
      data: {
        points: [{
          category: "model=a",
          displayCategory: "Model A",
          series: "__single__",
          displaySeries: "__single__",
          samples: [0.75],
        }],
      },
    }],
  };

  const result = await downloadActivePlotData({
    state: createPlotState({ activePlotDownloadData: payload }),
    save: async ({ blob, suggestedName, types }) => {
      saved = { blob, suggestedName, types };
      return true;
    },
  });

  assert.equal(result, true);
  assert.equal(saved.suggestedName, "experiment - a-score-data.json");
  assert.equal(saved.blob.type, "application/json");
  assert.deepEqual(JSON.parse(await saved.blob.text()), expectedJson);
  assert.deepEqual(saved.types[0].accept, { "application/json": [".json"] });

  assert.equal(
    await downloadActivePlotData({
      state: createPlotState({ activePlotDownloadData: { plots: [] } }),
      save: async () => {
        throw new Error("save should not be called");
      },
    }),
    false
  );
});

/**
 * Verify malformed active plot download state fails loudly instead of exporting ambiguous JSON.
 */
test("dashboard data download helper rejects unsupported metric families", () => {
  assert.throws(
    () => buildJsonSafeActivePlotDownloadData({
      metric_family: "unknown",
      plot_tab: "score",
      plots: [{ metaData: {}, dataSource: { points: [] } }],
    }),
    /Unsupported active plot download metric family: unknown/
  );
});

/**
 * Verify the dashboard-level download helper builds and saves a ZIP from visible plot cards.
 */
test("dashboard download helper exports visible plot cards with active state", async () => {
  const documentLike = createDocumentStub();
  const previousXmlSerializer = globalThis.XMLSerializer;
  globalThis.XMLSerializer = class {
    serializeToString(svg) {
      return serializeFakeSvg(svg);
    }
  };
  const evalPlotContent = documentLike.createElement("div");
  const card = documentLike.createElement("section");
  card.className = "plot-card";
  const title = documentLike.createElement("p");
  title.className = "plot-title";
  title.textContent = "Score / Mean";
  card.appendChild(title);
  const svg = documentLike.createElementNS("", "svg");
  svg.setAttribute("width", "100");
  svg.setAttribute("height", "60");
  card.appendChild(svg);
  evalPlotContent.appendChild(card);

  const evalPlotTabs = documentLike.createElement("div");
  const activeTab = documentLike.createElement("button");
  activeTab.className = "tab-button active";
  activeTab.setAttribute("title", "score.mean");
  evalPlotTabs.appendChild(activeTab);

  let urlBlob = null;
  let revokedUrl = null;
  try {
    const result = await downloadVisiblePlotFigures({
      state: createPlotState({
        exportOpaqueBackground: true,
        activePlotLegendItems: [{ key: "score", label: "Score", color: "#111111" }],
      }),
      evalPlotContent,
      evalPlotTabs,
      documentLike,
      windowLike: {},
      urlLike: {
        createObjectURL: (blob) => {
          urlBlob = blob;
          return "blob:figures";
        },
        revokeObjectURL: (url) => {
          revokedUrl = url;
        },
      },
      setTimeoutLike: (callback) => callback(),
      getStyle: () => ({ backgroundColor: "#ffffff", color: "#000000", font: "12px sans-serif" }),
    });

    assert.equal(result, true);
    assert.equal(urlBlob.type, "application/zip");
    assert.equal(revokedUrl, "blob:figures");
  } finally {
    globalThis.XMLSerializer = previousXmlSerializer;
  }
});

/**
 * Verify plot-control synchronization is delegated through the dashboard adapter.
 */
test("dashboard control helper mirrors plot settings into DOM inputs", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  renderDashboardPlotControls({
    state: createPlotState({
      plotShortenLabels: true,
      plotRoundingPrecision: 2,
      plotTpFpFnMinLabelTotal: 5,
      exportOpaqueBackground: true,
    }),
    dom,
    metricType: "TpFpFnCollector",
  });

  assert.equal(dom.plotShortenLabels.checked, true);
  assert.equal(dom.plotRoundingPrecision.value, "2");
  assert.equal(dom.plotTpFpFnMinLabelTotal.value, "5");
  assert.equal(dom.exportOpaqueBackground.checked, true);
  assert.equal(dom.plotTpFpFnMinLabelTotalRow.style.display, "");
  assert.equal(dom.plotGroupBarsRow.style.display, "none");
});

/**
 * Verify the dashboard render adapter creates tabbed bar plots from selected evaluation data.
 */
test("dashboard render adapter renders bar-like plot cards", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState();
  const evaluationContext = {
    experimentEvaluations: [{ data: { score: { mean: 0.75 } } }],
    evalTabState: { groupByFields: [] },
  };

  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment: "experiment/a",
    evaluationContext,
    documentLike,
    requestAnimationFrameLike: (callback) => callback(),
    plotTooltipHandlers: { show: () => {}, move: () => {}, hide: () => {} },
    getSelectedPredictionGroups: () => [{}],
    getSelectedEvaluationGroups: () => [{ evaluations: [{ data: { score: { mean: 0.75 } } }] }],
    getMetricTypeForEvaluationContext: () => "F1MicroMultipleFieldsMetric",
    getPlotGroups: () => ({
      fields: [],
      groups: [{ groupId: "all", values: {}, evaluations: [{ data: { score: { mean: 0.75 } } }] }],
    }),
    getEvaluationEffectiveValue: () => null,
    getEvaluationExperiment: () => "experiment/a",
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  assert.equal(state.activeEvalPlotTab, "score");
  assert.equal(dom.evalPlotTabs.querySelector("button").textContent, "score (1)");
  assert.equal(dom.evalPlotContent.querySelector(".plot-card").querySelector(".plot-title").textContent, "score.mean (mean ± std)");
  assert.equal(dom.evalPlotContent.querySelector("svg").tagName, "svg");
  assert.equal(state.activePlotDownloadData.metric_family, "numeric");
  assert.equal(state.activePlotDownloadData.plot_tab, "score");
  assert.deepEqual(state.activePlotDownloadData.plots[0].metaData, {
    metricLabel: "score.mean",
  });
  assert.deepEqual(state.activePlotDownloadData.plots[0].dataSource.points, [{
    label: "group 1",
    displayLabel: "group 1",
    category: "group 1",
    displayCategory: "group 1",
    series: "__single__",
    displaySeries: "__single__",
    samples: [0.75],
  }]);
  const downloadPayload = buildJsonSafeActivePlotDownloadData(state.activePlotDownloadData);
  assert.deepEqual(downloadPayload, {
    metric_family: "numeric",
    plot_tab: "score",
    plots: [{
      metaData: {
        metricLabel: "score.mean",
      },
      data: {
        points: [{
          category: "group 1",
          displayCategory: "group 1",
          series: "__single__",
          displaySeries: "__single__",
          samples: [0.75],
        }],
      },
    }],
  });
  assert.equal("mean" in downloadPayload.plots[0].data.points[0], false);
  assert.equal("std" in downloadPayload.plots[0].data.points[0], false);
});

/**
 * Verify the dashboard render adapter routes confusion-matrix plots through the extracted branch.
 */
test("dashboard render adapter renders confusion-matrix plot cards", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState({ plotConfusionMinLabelTotal: 1 });
  const evaluations = [
    {
      runDir: "run-a",
      overrides: { experiment: "experiment/a", "metric.field": "field_a" },
      jobReturnValue: { type: "ConfusionMatrix" },
      data: { actual: { predicted: 2 } },
    },
  ];
  const evaluationContext = {
    experimentEvaluations: evaluations,
    evalTabState: { groupByFields: ["model"] },
  };

  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment: "experiment/a",
    evaluationContext,
    documentLike,
    plotTooltipHandlers: { show: () => {}, move: () => {}, hide: () => {} },
    getSelectedPredictionGroups: () => [{}],
    getSelectedEvaluationGroups: () => [{ evaluations }],
    getMetricTypeForEvaluationContext: () => "ConfusionMatrix",
    getPlotGroups: () => ({
      fields: ["model"],
      groups: [{ groupId: "g1", values: { model: "a" }, evaluations }],
    }),
    getEvaluationEffectiveValue: (evaluation, column) => evaluation.overrides?.[column] ?? "",
    getEvaluationExperiment: (evaluation) => evaluation.overrides.experiment,
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  assert.equal(state.activeEvalPlotTab, "field_a");
  assert.equal(dom.evalPlotTabs.querySelector("button").textContent, "field_a (1)");
  assert.equal(dom.evalPlotContent.querySelector(".plot-card").querySelector(".plot-title").textContent, "model=a (mean ± std)");
  assert.ok(dom.evalPlotContent.querySelectorAll("text").some((text) => text.textContent === "actual"));
  assert.equal(state.activePlotDownloadData.metric_family, "confusion_matrix");
  assert.deepEqual(state.activePlotDownloadData.plots[0].metaData, {
    label: "model=a",
    fieldLabel: "field_a",
  });
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.rows[0], "actual");
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.cols[0], "predicted");
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.evaluationCells[0].get("actual|#|predicted"), 2);
  assert.deepEqual(buildJsonSafeActivePlotDownloadData(state.activePlotDownloadData).plots[0], {
    metaData: {
      label: "model=a",
      fieldLabel: "field_a",
    },
    data: {
      rows: ["actual"],
      cols: ["predicted"],
      evaluationCells: [[["actual|#|predicted", 2]]],
    },
  });
  assert.equal("collections" in state.activePlotDownloadData.plots[0].metaData, false);
});

/**
 * Verify confusion-matrix download data remains pre-filter and sparse.
 */
test("dashboard confusion download data keeps unfiltered sparse matrix input", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState({ plotConfusionMinLabelTotal: 2 });
  const evaluations = [
    {
      runDir: "run-a",
      overrides: { experiment: "experiment/a", "metric.field": "field_a" },
      jobReturnValue: { type: "ConfusionMatrix" },
      data: {
        actual: { predicted: 2 },
        filtered: { hidden: 1 },
      },
    },
  ];
  const evaluationContext = {
    experimentEvaluations: evaluations,
    evalTabState: { groupByFields: ["model"] },
  };

  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment: "experiment/a",
    evaluationContext,
    documentLike,
    plotTooltipHandlers: { show: () => {}, move: () => {}, hide: () => {} },
    getSelectedPredictionGroups: () => [{}],
    getSelectedEvaluationGroups: () => [{ evaluations }],
    getMetricTypeForEvaluationContext: () => "ConfusionMatrix",
    getPlotGroups: () => ({
      fields: ["model"],
      groups: [{ groupId: "g1", values: { model: "a" }, evaluations }],
    }),
    getEvaluationEffectiveValue: (evaluation, column) => evaluation.overrides?.[column] ?? "",
    getEvaluationExperiment: (evaluation) => evaluation.overrides.experiment,
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  const renderedText = dom.evalPlotContent.querySelectorAll("text").map((text) => text.textContent);
  assert.equal(renderedText.includes("actual"), true);
  assert.equal(renderedText.includes("filtered"), false);
  assert.deepEqual(buildJsonSafeActivePlotDownloadData(state.activePlotDownloadData).plots[0].data, {
    rows: ["actual", "filtered"],
    cols: ["hidden", "predicted"],
    evaluationCells: [[
      ["actual|#|predicted", 2],
      ["filtered|#|hidden", 1],
    ]],
  });
});

/**
 * Verify the dashboard render adapter routes TP/FP/FN collector plots through the extracted branch.
 */
test("dashboard render adapter renders TP/FP/FN plot cards", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState({ plotTpFpFnMinLabelTotal: 1 });
  const evaluations = [
    {
      runDir: "run-a",
      overrides: { "metric.field": "field_a" },
      jobReturnValue: { type: "TpFpFnCollector" },
      data: { doc1: { tp: ["label"], fp: [], fn: [] } },
    },
  ];
  const evaluationContext = {
    experimentEvaluations: evaluations,
    evalTabState: { groupByFields: ["model"] },
  };

  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment: "experiment/a",
    evaluationContext,
    documentLike,
    requestAnimationFrameLike: (callback) => callback(),
    navigatorLike: {},
    consoleLike: { warn: () => {} },
    plotTooltipHandlers: { show: () => {}, move: () => {}, hide: () => {} },
    getSelectedPredictionGroups: () => [{}],
    getSelectedEvaluationGroups: () => [{ evaluations }],
    getMetricTypeForEvaluationContext: () => "TpFpFnCollector",
    getPlotGroups: () => ({
      fields: ["model"],
      groups: [{ groupId: "g1", values: { model: "a" }, evaluations }],
    }),
    getEvaluationEffectiveValue: (evaluation, column) => evaluation.overrides?.[column] ?? "",
    getEvaluationExperiment: () => "experiment/a",
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  assert.equal(state.activeEvalPlotTab, "field_a");
  assert.equal(dom.evalPlotTabs.querySelector("button").textContent, "field_a (1)");
  assert.equal(dom.evalPlotContent.querySelector(".plot-legend").children.length, 3);
  assert.equal(dom.evalPlotContent.querySelector(".plot-card").querySelector(".plot-title").textContent, "model=a (1 grouped evals)");
  assert.ok(dom.evalPlotContent.querySelectorAll("text").some((text) => text.textContent === "doc1"));
  assert.equal(state.activePlotDownloadData.metric_family, "tpfpfn");
  assert.deepEqual(state.activePlotDownloadData.plots[0].metaData, {
    label: "model=a",
    fieldLabel: "field_a",
  });
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.rows[0], "doc1");
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.cols[0], "label");
  assert.deepEqual(state.activePlotDownloadData.plots[0].dataSource.evaluationCells[0].get("doc1|#|label"), {
    tp: true,
    fp: false,
    fn: false,
  });
  assert.deepEqual(buildJsonSafeActivePlotDownloadData(state.activePlotDownloadData).plots[0], {
    metaData: {
      label: "model=a",
      fieldLabel: "field_a",
    },
    data: {
      rows: ["doc1"],
      cols: ["label"],
      evaluationCells: [[["doc1|#|label", {
          tp: true,
          fp: false,
          fn: false,
        }]]],
    },
  });
  assert.equal("collections" in state.activePlotDownloadData.plots[0].metaData, false);
});

/**
 * Verify TP/FP/FN download data remains pre-filter and sparse.
 */
test("dashboard TP/FP/FN download data keeps unfiltered sparse matrix input", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState({
    plotTpFpFnMinLabelTotal: 2,
    plotTpFpFnMinDocumentTotal: 1,
  });
  const evaluations = [
    {
      runDir: "run-a",
      overrides: { "metric.field": "field_a" },
      jobReturnValue: { type: "TpFpFnCollector" },
      data: {
        doc1: { tp: ["label"], fp: [], fn: [] },
        filtered: { tp: [], fp: [], fn: ["hidden"] },
      },
    },
    {
      runDir: "run-b",
      overrides: { "metric.field": "field_a" },
      jobReturnValue: { type: "TpFpFnCollector" },
      data: {
        doc1: { tp: [], fp: [], fn: ["label"] },
      },
    },
  ];
  const evaluationContext = {
    experimentEvaluations: evaluations,
    evalTabState: { groupByFields: ["model"] },
  };

  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment: "experiment/a",
    evaluationContext,
    documentLike,
    requestAnimationFrameLike: (callback) => callback(),
    navigatorLike: {},
    consoleLike: { warn: () => {} },
    plotTooltipHandlers: { show: () => {}, move: () => {}, hide: () => {} },
    getSelectedPredictionGroups: () => [{}],
    getSelectedEvaluationGroups: () => [{ evaluations }],
    getMetricTypeForEvaluationContext: () => "TpFpFnCollector",
    getPlotGroups: () => ({
      fields: ["model"],
      groups: [{ groupId: "g1", values: { model: "a" }, evaluations }],
    }),
    getEvaluationEffectiveValue: (evaluation, column) => evaluation.overrides?.[column] ?? "",
    getEvaluationExperiment: () => "experiment/a",
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  const renderedText = dom.evalPlotContent.querySelectorAll("text").map((text) => text.textContent);
  assert.equal(renderedText.includes("doc1"), true);
  assert.equal(renderedText.includes("filtered"), false);
  assert.deepEqual(buildJsonSafeActivePlotDownloadData(state.activePlotDownloadData).plots[0].data, {
    rows: ["doc1", "filtered"],
    cols: ["hidden", "label"],
    evaluationCells: [
      [
        ["doc1|#|label", { tp: true, fp: false, fn: false }],
        ["filtered|#|hidden", { tp: false, fp: false, fn: true }],
      ],
      [
        ["doc1|#|label", { tp: false, fp: false, fn: true }],
      ],
    ],
  });
});
