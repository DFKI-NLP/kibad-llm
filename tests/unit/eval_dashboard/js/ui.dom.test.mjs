import test from "node:test";
import assert from "node:assert/strict";

import { captureDomRefs, setPanelVisibility } from "../../../../docs/eval-dashboard/assets/js/ui/dom.js";

const DOM_REF_IDS = [
  "folderInput",
  "gitUrlInput",
  "githubTokenInput",
  "loadGitButton",
  "loadStatus",
  "loadProgressWrap",
  "loadProgress",
  "loadProgressLabel",
  "predictionSummary",
  "groupByAllButton",
  "groupByNoneButton",
  "groupByToggleButton",
  "predictionSortedByLabel",
  "predictionResetSortButton",
  "optionsTabs",
  "truncateColumnsList",
  "predictionDefaultsPanel",
  "predictionDefaultsList",
  "truncateDefaultsButton",
  "predictionsTable",
  "evalTabs",
  "evalSummary",
  "evalGroupByAllButton",
  "evalGroupByNoneButton",
  "evalGroupByToggleButton",
  "evalSortedByLabel",
  "evalResetSortButton",
  "evalOptionsTabs",
  "evalTruncateColumnsList",
  "evalDefaultsPanel",
  "evalDefaultsList",
  "evalLayout",
  "evalJsonTabEvaluation",
  "evalJsonTabPrediction",
  "evalJsonTitle",
  "evalJsonCode",
  "evaluationsTable",
  "plotTabsByPrefixButton",
  "plotTabsBySuffixButton",
  "plotShortenLabels",
  "plotRoundingPrecision",
  "plotConfusionMinLabelTotalRow",
  "plotConfusionMinLabelTotal",
  "plotTpFpFnMinLabelTotalRow",
  "plotTpFpFnMinLabelTotal",
  "plotTpFpFnMinDocumentTotalRow",
  "plotTpFpFnMinDocumentTotal",
  "plotTabsByRow",
  "plotConfusionTabsByRow",
  "confusionTabsByMetricFieldButton",
  "confusionTabsByPredictionGroupButton",
  "plotGroupBarsRow",
  "plotGroupBarsList",
  "plotShowLegendOnceRow",
  "plotShowLegendOnce",
  "downloadFiguresButton",
  "exportOpaqueBackground",
  "evalPlotTabs",
  "evalPlotContent",
  "barTooltip",
];

function createElement(id) {
  return {
    id,
    style: { display: "" },
    queryResults: new Map(),
    querySelectorAll(selector) {
      return this.queryResults.get(selector) || [];
    },
  };
}

function createDocumentStub() {
  const elements = new Map(DOM_REF_IDS.map((id) => [id, createElement(id)]));
  const optionsTabButtons = [createElement("options-tab-button-1"), createElement("options-tab-button-2")];
  const evalOptionsTabButtons = [createElement("eval-options-tab-button-1")];
  const optionsTabPanels = [createElement("options-tab-panel-1"), createElement("options-tab-panel-2")];
  const evalOptionsTabPanels = [createElement("eval-options-tab-panel-1")];

  elements.get("optionsTabs").queryResults.set(".options-tab-button", optionsTabButtons);
  elements.get("evalOptionsTabs").queryResults.set(".options-tab-button", evalOptionsTabButtons);

  return {
    elements,
    optionsTabButtons,
    evalOptionsTabButtons,
    optionsTabPanels,
    evalOptionsTabPanels,
    documentLike: {
      getElementById(id) {
        return elements.get(id) || null;
      },
      querySelectorAll(selector) {
        if (selector === ".options-tab-panel") {
          return optionsTabPanels;
        }
        if (selector === ".options-tab-panel[data-eval-tab-panel]") {
          return evalOptionsTabPanels;
        }
        return [];
      },
    },
  };
}

test("captureDomRefs returns the stable dashboard ids plus the shared options-tab query results", () => {
  const { elements, optionsTabButtons, evalOptionsTabButtons, optionsTabPanels, evalOptionsTabPanels, documentLike } =
    createDocumentStub();

  const refs = captureDomRefs(documentLike);

  for (const id of DOM_REF_IDS) {
    assert.equal(refs[id], elements.get(id));
  }
  assert.deepEqual(refs.optionsTabButtons, optionsTabButtons);
  assert.deepEqual(refs.evalOptionsTabButtons, evalOptionsTabButtons);
  assert.deepEqual(refs.optionsTabPanels, optionsTabPanels);
  assert.deepEqual(refs.evalOptionsTabPanels, evalOptionsTabPanels);
});

test("captureDomRefs tolerates missing elements and missing query matches", () => {
  const refs = captureDomRefs({
    getElementById() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
  });

  assert.equal(refs.folderInput, null);
  assert.deepEqual(refs.optionsTabButtons, []);
  assert.deepEqual(refs.optionsTabPanels, []);
  assert.deepEqual(refs.evalOptionsTabButtons, []);
  assert.deepEqual(refs.evalOptionsTabPanels, []);
});

test("setPanelVisibility preserves the existing display contract and ignores null panels", () => {
  const panel = createElement("predictionDefaultsPanel");

  setPanelVisibility(panel, false);
  assert.equal(panel.style.display, "none");

  setPanelVisibility(panel, true);
  assert.equal(panel.style.display, "");

  assert.doesNotThrow(() => setPanelVisibility(null, false));
});
