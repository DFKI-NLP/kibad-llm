/**
 * Tests for the eval-dashboard plot-surface adapter.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  appendPlotEmptyMessage,
  buildActiveTabDownloadEnvelope,
  createPlotCard,
  createPlotGrid,
  createPlotTooltipHandlers,
  downloadVisiblePlotFigures,
  renderDashboardPlotControls,
  renderEvaluationPlotsForDashboard,
  renderPlotTabButtonModels,
  resolvePlotExportBackgroundColor,
  updateDownloadDataButtonState,
  updateDownloadFiguresButtonState,
} from "../../../../docs/eval-dashboard/assets/js/plots/dashboard.js";
import {
  buildDownloadPlotMetadata,
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
 * Verify concrete active-tab DOM helpers preserve the shared plot markup contract.
 */
test("dashboard active-tab helpers render tabs, cards, grids, empty states, and downloads", () => {
  const documentLike = createDocumentStub();
  const tabs = documentLike.createElement("div");
  let selected = null;
  renderPlotTabButtonModels({
    documentLike,
    containerElement: tabs,
    tabModels: [
      { value: "active", label: "Active", isActive: true },
      { value: "other", label: "Other" },
    ],
    activeKey: "active",
    onActiveTabChange: (key) => {
      selected = key;
    },
  });
  tabs.querySelectorAll("button")[0].click();
  assert.equal(selected, null);
  tabs.querySelectorAll("button")[1].click();
  assert.equal(selected, "other");

  const grid = createPlotGrid(documentLike);
  grid.appendChild(createPlotCard(documentLike, "Plot title"));
  assert.equal(grid.className, "plot-grid");
  assert.equal(grid.querySelector(".plot-title").textContent, "Plot title");

  const content = documentLike.createElement("div");
  appendPlotEmptyMessage(documentLike, content, "Nothing to plot.");
  assert.equal(content.querySelector(".plot-empty").textContent, "Nothing to plot.");

  const plots = [{ metadata: {}, dataSource: new Map() }];
  assert.deepEqual(
    buildActiveTabDownloadEnvelope(
      "confusion_matrix",
      { plotTab: "field", plotTabVariant: "metric_field" },
      plots
    ),
    {
      metric_family: "confusion_matrix",
      plot_tab: "field",
      plot_tab_variant: "metric_field",
      plots,
    }
  );
});

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
    plot_tab_variant: "prefix",
    plots: [{
      metadata: { metric_label: "score.mean" },
      dataSource: {
        points: [{
          category: "model=a",
          displayCategory: "Model A",
          series: "__single__",
          displaySeries: "__single__",
          runDirs: ["run-a"],
          samples: [0.75],
        }],
      },
    }],
  };
  const expectedJson = {
    metric_family: "numeric",
    plot_tab: "score",
    plot_tab_variant: "prefix",
    plots: [{
      metadata: { metric_label: "score.mean" },
      data: {
        points: [{
          category: "model=a",
          display_category: "Model A",
          series: "__single__",
          display_series: "__single__",
          run_dirs: ["run-a"],
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
      plots: [{ metadata: {}, dataSource: { points: [] } }],
    }),
    /Unsupported active plot download metric family: unknown/
  );
  assert.throws(
    () => buildDownloadPlotMetadata("unknown", {}),
    /Unsupported download metadata metric family: unknown/
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
  const evaluation = { runDir: "run-a", data: { score: { mean: 0.75 } } };
  const evaluationContext = {
    experimentEvaluations: [evaluation],
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
    getSelectedEvaluationGroups: () => [{ evaluations: [evaluation] }],
    getMetricTypeForEvaluationContext: () => "F1MicroMultipleFieldsMetric",
    getPlotGroups: () => ({
      fields: [],
      groups: [{ groupId: "all", values: {}, evaluations: [evaluation] }],
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
  assert.equal(state.activePlotDownloadData.plot_tab_variant, "prefix");
  assert.deepEqual(state.activePlotDownloadData.plots[0].metadata, {
    metric_label: "score.mean",
  });
  assert.deepEqual(state.activePlotDownloadData.plots[0].dataSource.points, [{
    label: "group 1",
    displayLabel: "group 1",
    category: "group 1",
    displayCategory: "group 1",
    series: "__single__",
    displaySeries: "__single__",
    runDirs: ["run-a"],
    samples: [0.75],
  }]);
  const downloadPayload = buildJsonSafeActivePlotDownloadData(state.activePlotDownloadData);
  assert.deepEqual(downloadPayload, {
    metric_family: "numeric",
    plot_tab: "score",
    plot_tab_variant: "prefix",
    plots: [{
      metadata: {
        metric_label: "score.mean",
      },
      data: {
        points: [{
          category: "group 1",
          display_category: "group 1",
          series: "__single__",
          display_series: "__single__",
          run_dirs: ["run-a"],
          samples: [0.75],
        }],
      },
    }],
  });
  assert.equal("mean" in downloadPayload.plots[0].data.points[0], false);
  assert.equal("std" in downloadPayload.plots[0].data.points[0], false);
});

/**
 * Verify grouped numeric orchestration preserves shared and per-card legend behavior.
 */
test("dashboard renders grouped numeric legends and export legend state", () => {
  for (const plotShowLegendOnce of [true, false]) {
    const documentLike = createDocumentStub();
    const dom = createPlotDom(documentLike);
    const state = createPlotState({
      plotGroupBarFields: new Set(["seed"]),
      plotShowLegendOnce,
    });
    const evaluations = [
      { runDir: "run-a-1", data: { score: { mean: 0.5 } } },
      { runDir: "run-a-2", data: { score: { mean: 0.6 } } },
      { runDir: "run-b-1", data: { score: { mean: 0.7 } } },
      { runDir: "run-b-2", data: { score: { mean: 0.8 } } },
    ];
    const plotGroups = [
      {
        groupId: "a-1",
        values: { model: "a", seed: "1" },
        evaluations: [evaluations[0]],
      },
      {
        groupId: "a-2",
        values: { model: "a", seed: "2" },
        evaluations: [evaluations[1]],
      },
      {
        groupId: "b-1",
        values: { model: "b", seed: "1" },
        evaluations: [evaluations[2]],
      },
      {
        groupId: "b-2",
        values: { model: "b", seed: "2" },
        evaluations: [evaluations[3]],
      },
    ];

    renderEvaluationPlotsForDashboard({
      state,
      dom,
      activeExperiment: "experiment/a",
      evaluationContext: {
        experimentEvaluations: evaluations,
        evalTabState: { groupByFields: ["model", "seed"] },
      },
      documentLike,
      requestAnimationFrameLike: (callback) => callback(),
      plotTooltipHandlers: { show: () => {}, move: () => {}, hide: () => {} },
      getSelectedPredictionGroups: () => [{}],
      getSelectedEvaluationGroups: () => [{ evaluations }],
      getMetricTypeForEvaluationContext: () => "F1MicroMultipleFieldsMetric",
      getPlotGroups: () => ({
        fields: ["model", "seed"],
        groups: plotGroups,
      }),
      getEvaluationEffectiveValue: () => null,
      getEvaluationExperiment: () => "experiment/a",
      displayPlotGroupFieldName: (field) => field,
      displayGroupFieldName: (field) => field,
      getPlotDisplayLabel: (label) => label,
      getPlotTitleLabel: (entry) => entry.metricLabel,
      rerenderEvaluationPlots: () => {},
    });

    const legends = dom.evalPlotContent.querySelectorAll(".plot-legend");
    assert.equal(legends.length, 1);
    assert.deepEqual(
      legends[0].querySelectorAll(".plot-legend-item").map((item) => item.children[1].textContent),
      ["seed=1", "seed=2"]
    );
    assert.equal(
      dom.evalPlotContent.querySelector(".plot-title").textContent,
      "score.mean (mean ± std) | grouped by: seed"
    );
    assert.equal(dom.evalPlotContent.querySelector(".plot-card").querySelector("svg").tagName, "svg");
    assert.equal(dom.plotShowLegendOnceRow.style.display, "");
    assert.deepEqual(
      state.activePlotLegendItems.map((item) => item.label),
      ["seed=1", "seed=2"]
    );
    assert.equal(
      dom.evalPlotContent.children[0].className,
      plotShowLegendOnce ? "plot-legend" : "plot-grid"
    );
    assert.equal(
      dom.evalPlotContent.querySelector(".plot-card").querySelector(".plot-legend") !== null,
      !plotShowLegendOnce
    );
  }
});

/**
 * Verify numeric sample preparation is limited to definitions in the active tab.
 */
test("dashboard prepares numeric plot data only for the active tab", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState({ activeEvalPlotTab: "active" });
  const evaluations = [
    {
      runDir: "run-a",
      data: { active: { value: 0.5 }, inactive: { value: 0.7 } },
    },
    {
      runDir: "run-b",
      data: { active: { value: 0.9 } },
    },
  ];
  const evaluationContext = {
    experimentEvaluations: evaluations,
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
    getSelectedEvaluationGroups: () => [{ evaluations }],
    getMetricTypeForEvaluationContext: () => "F1MicroMultipleFieldsMetric",
    getPlotGroups: () => ({
      fields: [],
      groups: [{ groupId: "all", values: {}, evaluations }],
    }),
    getEvaluationEffectiveValue: () => null,
    getEvaluationExperiment: () => "experiment/a",
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  assert.equal(state.activeEvalPlotTab, "active");
  assert.deepEqual(
    Array.from(dom.evalPlotTabs.querySelectorAll("button"), (button) => button.textContent),
    ["active (1)", "inactive (1)"]
  );
  assert.deepEqual(
    state.activePlotDownloadData.plots.map((plot) => plot.metadata.metric_label),
    ["active.value"]
  );
});

/**
 * Verify inactive confusion tabs never prepare their collection data.
 */
test("dashboard prepares confusion data only for the active tab", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState({
    activeEvalPlotTab: "active_field",
    plotConfusionMinLabelTotal: 1,
  });
  const activeEvaluation = {
    runId: "run-active-id",
    runDir: "run-active",
    overrides: { experiment: "experiment/a", "metric.field": "active_field" },
    jobReturnValue: { type: "ConfusionMatrix" },
    data: { actual: { predicted: 2 } },
  };
  const inactiveEvaluation = {
    runId: "run-inactive-id",
    runDir: "run-inactive",
    overrides: { experiment: "experiment/a", "metric.field": "inactive_field" },
    jobReturnValue: { type: "ConfusionMatrix" },
    data: { "invalid|#|row": { predicted: 1 } },
  };
  const evaluations = [activeEvaluation, inactiveEvaluation];

  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment: "experiment/a",
    evaluationContext: {
      experimentEvaluations: evaluations,
      evalTabState: { groupByFields: [] },
    },
    documentLike,
    plotTooltipHandlers: { show: () => {}, move: () => {}, hide: () => {} },
    getSelectedPredictionGroups: () => [{}],
    getSelectedEvaluationGroups: () => [{ evaluations }],
    getMetricTypeForEvaluationContext: () => "ConfusionMatrix",
    getPlotGroups: () => ({
      fields: [],
      groups: [{ groupId: "all", values: {}, evaluations }],
    }),
    getEvaluationEffectiveValue: (evaluation, column) => evaluation.overrides?.[column] ?? "",
    getEvaluationExperiment: (evaluation) => evaluation.overrides.experiment,
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  assert.equal(state.activeEvalPlotTab, "active_field");
  assert.deepEqual(
    Array.from(dom.evalPlotTabs.querySelectorAll("button"), (button) => button.textContent),
    ["active_field (1)", "inactive_field (1)"]
  );
  assert.equal(inactiveEvaluation.dataPrepared, undefined);
  assert.deepEqual(
    state.activePlotDownloadData.plots.map((plot) => plot.metadata.field_label),
    ["active_field"]
  );
});

/**
 * Verify inactive TP/FP/FN tabs never prepare their collection data.
 */
test("dashboard prepares TP/FP/FN data only for the active tab", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState({
    activeEvalPlotTab: "active_field",
    plotTpFpFnMinLabelTotal: 1,
  });
  const activeEvaluation = {
    runDir: "run-active",
    overrides: { "metric.field": "active_field" },
    jobReturnValue: { type: "TpFpFnCollector" },
    data: { doc1: { tp: ["label"], fp: [], fn: [] } },
  };
  const inactiveEvaluation = {
    runDir: "run-inactive",
    overrides: { "metric.field": "inactive_field" },
    jobReturnValue: { type: "TpFpFnCollector" },
    data: { "invalid|#|document": { tp: ["label"], fp: [], fn: [] } },
  };
  const evaluations = [activeEvaluation, inactiveEvaluation];

  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment: "experiment/a",
    evaluationContext: {
      experimentEvaluations: evaluations,
      evalTabState: { groupByFields: [] },
    },
    documentLike,
    requestAnimationFrameLike: (callback) => callback(),
    navigatorLike: {},
    consoleLike: { warn: () => {} },
    plotTooltipHandlers: { show: () => {}, move: () => {}, hide: () => {} },
    getSelectedPredictionGroups: () => [{}],
    getSelectedEvaluationGroups: () => [{ evaluations }],
    getMetricTypeForEvaluationContext: () => "TpFpFnCollector",
    getPlotGroups: () => ({
      fields: [],
      groups: [{ groupId: "all", values: {}, evaluations }],
    }),
    getEvaluationEffectiveValue: (evaluation, column) => evaluation.overrides?.[column] ?? "",
    getEvaluationExperiment: () => "experiment/a",
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  assert.equal(state.activeEvalPlotTab, "active_field");
  assert.deepEqual(
    Array.from(dom.evalPlotTabs.querySelectorAll("button"), (button) => button.textContent),
    ["active_field (1)", "inactive_field (1)"]
  );
  assert.equal(inactiveEvaluation.dataPrepared, undefined);
  assert.deepEqual(
    state.activePlotDownloadData.plots.map((plot) => plot.metadata.field_label),
    ["active_field"]
  );
});

/**
 * Verify numeric path discovery cannot leak metrics from unselected evaluation groups.
 */
test("dashboard numeric plots discover metrics only from selected plot groups", () => {
  const documentLike = createDocumentStub();
  const dom = createPlotDom(documentLike);
  const state = createPlotState();
  const selectedEvaluation = {
    runDir: "run-a",
    data: { no_error: 100 },
  };
  const unselectedEvaluation = {
    runDir: "run-b",
    data: { no_error: 90, ValueError: 10 },
  };
  const evaluationContext = {
    experimentEvaluations: [selectedEvaluation, unselectedEvaluation],
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
    getSelectedEvaluationGroups: () => [{ evaluations: [selectedEvaluation] }],
    getMetricTypeForEvaluationContext: () => "ErrorCollector",
    getPlotGroups: () => ({
      fields: [],
      groups: [{ groupId: "selected", values: {}, evaluations: [selectedEvaluation] }],
    }),
    getEvaluationEffectiveValue: () => null,
    getEvaluationExperiment: () => "experiment/a",
    displayPlotGroupFieldName: (field) => field,
    displayGroupFieldName: (field) => field,
    getPlotDisplayLabel: (label) => label,
    getPlotTitleLabel: (entry) => entry.metricLabel,
    rerenderEvaluationPlots: () => {},
  });

  assert.equal(state.activeEvalPlotTab, "total");
  assert.equal(state.activePlotDownloadData.plot_tab, "total");
  assert.equal(state.activePlotDownloadData.plot_tab_variant, "error_section");
  assert.deepEqual(
    state.activePlotDownloadData.plots.map((plot) => plot.metadata.metric_label),
    ["no_error"]
  );
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
      runId: "run-a-id",
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
  assert.equal(state.activePlotDownloadData.plot_tab, "field_a");
  assert.equal(state.activePlotDownloadData.plot_tab_variant, "metric_field");
  assert.deepEqual(state.activePlotDownloadData.plots[0].metadata, {
    label: "model=a",
    field_label: "field_a",
  });
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.rows[0], "actual");
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.cols[0], "predicted");
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.cells[0].get("actual|#|predicted"), 2);
  assert.deepEqual(buildJsonSafeActivePlotDownloadData(state.activePlotDownloadData).plots[0], {
    metadata: {
      label: "model=a",
      field_label: "field_a",
    },
    data: {
      rows: ["actual"],
      columns: ["predicted"],
      run_dirs: ["run-a"],
      cells: [[["actual|#|predicted", 2]]],
    },
  });
  assert.equal("collections" in state.activePlotDownloadData.plots[0].metadata, false);
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
    columns: ["hidden", "predicted"],
    run_dirs: ["run-a"],
    cells: [[
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
  const state = createPlotState({
    plotTpFpFnMinLabelTotal: 1,
    confusionTabsBy: "prediction_group",
  });
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

  assert.equal(state.activeEvalPlotTab, "group|#|g1");
  assert.equal(dom.evalPlotTabs.querySelector("button").textContent, "model=a (1)");
  assert.equal(dom.evalPlotContent.querySelector(".plot-legend").children.length, 3);
  assert.equal(dom.evalPlotContent.querySelector(".plot-card").querySelector(".plot-title").textContent, "field_a (1 grouped evals)");
  assert.ok(dom.evalPlotContent.querySelectorAll("text").some((text) => text.textContent === "doc1"));
  assert.equal(state.activePlotDownloadData.metric_family, "tpfpfn");
  assert.equal(state.activePlotDownloadData.plot_tab, "g1");
  assert.equal(state.activePlotDownloadData.plot_tab_variant, "prediction_group");
  assert.deepEqual(state.activePlotDownloadData.plots[0].metadata, {
    label: "field_a",
    field_label: "field_a",
  });
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.rows[0], "doc1");
  assert.equal(state.activePlotDownloadData.plots[0].dataSource.cols[0], "label");
  assert.equal(
    state.activePlotDownloadData.plots[0].dataSource.cells[0].get("doc1|#|label"),
    "tp"
  );
  assert.deepEqual(buildJsonSafeActivePlotDownloadData(state.activePlotDownloadData).plots[0], {
    metadata: {
      label: "field_a",
      field_label: "field_a",
    },
    data: {
      rows: ["doc1"],
      columns: ["label"],
      run_dirs: ["run-a"],
      cells: [[["doc1|#|label", "tp"]]],
    },
  });
  assert.equal("collections" in state.activePlotDownloadData.plots[0].metadata, false);
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
    columns: ["hidden", "label"],
    run_dirs: ["run-a", "run-b"],
    cells: [
      [
        ["doc1|#|label", "tp"],
        ["filtered|#|hidden", "fn"],
      ],
      [
        ["doc1|#|label", "fn"],
      ],
    ],
  });
});
