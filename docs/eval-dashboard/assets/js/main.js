import { getValueAtPath } from "./utils/flatten.js";
import { normalizeSortConfig } from "./utils/sort.js";
import {
  getFigureTitlePrefix,
  sanitizeFigureFilename,
  splitLabelByLastDot,
} from "./utils/text.js";
import { formatRounded, interpolateColor, meanAndStd, normalizeValue } from "./utils/values.js";
import * as dashboardStore from "./state/store.js";
import * as selectors from "./state/selectors.js";
import { collectLocalEvaluationEntries } from "./data/file-loader.js";
import { ingestRunEntries } from "./data/ingest-runs.js";
import { loadGitHubEntriesFromTreeUrl } from "./data/git-loader.js";
import {
  clearGitUrlQueryParam,
  initializeGitHubTokenInput,
  persistGitHubTokenInputValue,
  runGitUrlQueryParamBootstrap,
  setGitUrlQueryParam,
} from "./browser/session.js";
import { captureDomRefs, setPanelVisibility } from "./ui/dom.js";
import {
  getToggleOnlyColumns,
  renderOptionsPanel,
  renderPlotControls,
  renderPlotGroupBarChips,
  renderGroupByButtonState,
  renderSortStatus,
} from "./ui/controls.js";
import {
  bindEvalJsonTabSelection,
  renderEvalJsonPane,
} from "./ui/eval-json-pane.js";
import {
  getNextSortConfig as getSharedNextSortConfig,
  updateStickyControlColumnOffsets,
} from "./ui/table-shared.js";
import { renderPredictionTable } from "./ui/prediction-table.js";
import { renderEvaluationTable } from "./ui/evaluation-table.js";
import {
  bindDelegatedTabSelection,
  buildCountTabButtonModels,
  renderTabButtons,
  renderStaticTabState,
  resolveActiveTabValue,
} from "./ui/tabs.js";
import {
  clearLoadProgress,
  renderDownloadFiguresButtonState,
  renderLoadProgress,
  renderLoadStatusStage,
  renderLoadStatusSummary,
  setDownloadFiguresButtonBusy,
} from "./ui/status.js";

// Central UI state: loaded prediction/evaluation data, current grouping/selection, and per-eval-tab view state.
const state = dashboardStore.createInitialDashboardState();

const dom = captureDomRefs(document);
const {
  folderInput,
  gitUrlInput,
  githubTokenInput,
  loadGitButton,
  predictionSummary,
  groupByAllButton,
  groupByNoneButton,
  groupByToggleButton,
  predictionSortedByLabel,
  predictionResetSortButton,
  optionsTabs,
  optionsTabButtons,
  optionsTabPanels,
  truncateColumnsList,
  predictionDefaultsPanel,
  predictionDefaultsList,
  truncateDefaultsButton,
  predictionsTable,
  evalTabs,
  evalSummary,
  evalGroupByAllButton,
  evalGroupByNoneButton,
  evalGroupByToggleButton,
  evalSortedByLabel,
  evalResetSortButton,
  evalOptionsTabs,
  evalOptionsTabButtons,
  evalOptionsTabPanels,
  evalTruncateColumnsList,
  evalDefaultsPanel,
  evalDefaultsList,
  evalLayout,
  evalJsonTabEvaluation,
  evalJsonTabPrediction,
  evalJsonTitle,
  evalJsonCode,
  evaluationsTable,
  plotTabsByPrefixButton,
  plotTabsBySuffixButton,
  plotShortenLabels,
  plotRoundingPrecision,
  plotConfusionMinLabelTotalRow,
  plotConfusionMinLabelTotal,
  plotTpFpFnMinLabelTotalRow,
  plotTpFpFnMinLabelTotal,
  plotTpFpFnMinDocumentTotalRow,
  plotTpFpFnMinDocumentTotal,
  plotTabsByRow,
  plotConfusionTabsByRow,
  confusionTabsByMetricFieldButton,
  confusionTabsByPredictionGroupButton,
  plotGroupBarsRow,
  plotGroupBarsList,
  plotShowLegendOnceRow,
  plotShowLegendOnce,
  downloadFiguresButton,
  exportOpaqueBackground,
  evalPlotTabs,
  evalPlotContent,
  barTooltip,
} = dom;
const { SORTABLE_CONTROL_COLUMNS } = dashboardStore;
const {
  EVALUATION_PREFIX,
  JOB_RETURN_VALUE_PREFIX,
  PREDICTION_JOB_RETURN_VALUE_PREFIX,
  PREDICTION_OVERRIDES_PREFIX,
} = selectors;
const TP_FP_FN_KEYS = ["tp", "fp", "fn"];
const sortCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

function getNextSortConfig(currentSort, column, { append = false } = {}) {
  return getSharedNextSortConfig(currentSort, column, {
    append,
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });
}

// Selectors and accessors for the canonical predictions/evaluations state shape.
function isJobReturnValueColumn(column) {
  return selectors.isJobReturnValueColumn(column);
}

function stripEvaluationFieldPrefix(column) {
  return selectors.stripEvaluationFieldPrefix(column);
}

function stripPredictionFieldPrefix(column) {
  return selectors.stripPredictionFieldPrefix(column);
}

function reconstructPredictionContent(prediction) {
  return selectors.reconstructPredictionContent(prediction);
}

function getPredictionById(predictionId) {
  return selectors.getPredictionById(state, predictionId);
}

function getPredictionForEvaluation(evaluation) {
  return selectors.getPredictionForEvaluation(state, evaluation);
}

function reconstructPredictionContentForEvaluation(evaluation) {
  return selectors.reconstructPredictionContentForEvaluation(state, evaluation);
}

function getFlattenedPrediction(prediction) {
  return selectors.getFlattenedPrediction(prediction);
}

function getFlattenedPredictionForEvaluation(evaluation) {
  return selectors.getFlattenedPredictionForEvaluation(state, evaluation);
}

/**
 * Derive one prediction view per canonical prediction id.
 * Each view joins the flattened prediction fields with all linked evaluations.
 */
function getPredictionViews() {
  return selectors.getPredictionViews(state);
}

/**
 * Collect all flattened prediction columns currently present across the given prediction views.
 */
function getPredictionColumns(predictionViews = getPredictionViews()) {
  return selectors.getPredictionColumns(predictionViews);
}

/**
 * Return the current prediction columns derived from canonical prediction state.
 */
function getCurrentPredictionColumns(predictionViews = getPredictionViews()) {
  return selectors.getCurrentPredictionColumns(state, predictionViews);
}

/**
 * Group prediction views according to the active prediction group-by fields.
 * The returned group shape matches the current prediction table/rendering expectations.
 */
function getPredictionGroups(
  predictionViews = getPredictionViews(),
  groupByFields = state.groupByFields,
  predictionColumns = getCurrentPredictionColumns(predictionViews)
) {
  return selectors.getPredictionGroups(state, predictionViews, groupByFields, predictionColumns);
}

/**
 * Filter prediction groups down to the currently selected prediction group ids.
 */
function getSelectedPredictionGroups(groups = getCurrentPredictionGroups()) {
  return selectors.getSelectedPredictionGroups(state, groups);
}

/**
 * Synchronize prediction-group UI state with the currently derived prediction groups.
 * This preserves selections for stable ids, auto-selects newly created groups, and drops stale expanded ids.
 */
function syncPredictionGroupUiState(predictionGroups) {
  dashboardStore.syncPredictionGroupUiState(state, predictionGroups);
}

/**
 * Return the current prediction groups derived from canonical state and current prediction UI settings.
 */
function getCurrentPredictionGroups() {
  const predictionViews = getPredictionViews();
  const predictionColumns = getCurrentPredictionColumns(predictionViews);
  const predictionGroups = getPredictionGroups(predictionViews, state.groupByFields, predictionColumns);
  syncPredictionGroupUiState(predictionGroups);
  return predictionGroups;
}

/**
 * Flatten the evaluations reachable from the selected prediction groups.
 */
function getSelectedEvaluations(selectedPredictionGroups = getSelectedPredictionGroups()) {
  return selectors.getSelectedEvaluations(selectedPredictionGroups);
}

function getFlattenedEvaluationJobReturnValue(evaluation) {
  return selectors.getFlattenedEvaluationJobReturnValue(evaluation);
}

function getEvaluationColumnRawValue(evaluation, column) {
  return selectors.getEvaluationColumnRawValue(evaluation, column);
}

function getEvaluationEffectiveValue(evaluation, column, evalTabState) {
  return selectors.getEvaluationEffectiveValue(evaluation, column, evalTabState);
}

function getEvaluationExperiment(evaluation) {
  return selectors.getEvaluationExperiment(evaluation);
}

/**
 * Flatten the currently selected prediction groups into their member prediction views.
 */
function getSelectedPredictionViews() {
  return selectors.getSelectedPredictionViews(state);
}

function gatherSelectedEvaluations() {
  return selectors.gatherSelectedEvaluations(state);
}

/**
 * Group the currently selected evaluations by evaluation experiment.
 */
function getEvaluationsByExperiment(selectedEvaluations = gatherSelectedEvaluations()) {
  return selectors.getEvaluationsByExperiment(state, selectedEvaluations);
}

/**
 * Return the selected evaluations that belong to one evaluation experiment.
 */
function getSelectedEvaluationsForExperiment(experiment, selectedEvaluations = gatherSelectedEvaluations()) {
  return selectors.getSelectedEvaluationsForExperiment(state, experiment, selectedEvaluations);
}

/**
 * Collect all evaluation columns currently present across the given evaluations.
 */
function getEvaluationColumns(evaluations = []) {
  return selectors.getEvaluationColumns(evaluations);
}

function showBarTooltip(event, lines) {
  barTooltip.textContent = lines.join("\n");
  barTooltip.style.display = "block";
  positionBarTooltip(event);
}

function positionBarTooltip(event) {
  const pad = 14;
  let x = event.clientX + pad;
  let y = event.clientY - pad - barTooltip.offsetHeight;
  if (x + barTooltip.offsetWidth > window.innerWidth - pad) {
    x = event.clientX - barTooltip.offsetWidth - pad;
  }
  if (y < pad) {
    y = event.clientY + pad;
  }
  barTooltip.style.left = `${x}px`;
  barTooltip.style.top = `${y}px`;
}

function hideBarTooltip() {
  barTooltip.style.display = "none";
}

async function writeTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "readonly");
  textarea.style.position = "fixed";
  textarea.style.top = "-9999px";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!copied) {
    throw new Error("Clipboard copy command was not successful.");
  }
}

function getUniqueFigureFilename(title, usedNames) {
  const baseName = sanitizeFigureFilename(getFigureTitlePrefix(title));
  let candidate = baseName;
  let suffix = 2;
  while (usedNames.has(candidate.toLowerCase())) {
    candidate = `${baseName} (${suffix})`;
    suffix += 1;
  }
  usedNames.add(candidate.toLowerCase());
  return `${candidate}.svg`;
}

function getActivePlotTabZipFilename() {
  const activeButton = evalPlotTabs.querySelector(".tab-button.active");
  const plotTabLabel = activeButton?.getAttribute("title") || activeButton?.textContent || "figures";
  const evalTabLabel = typeof state.activeEvalTab === "string" ? state.activeEvalTab.trim() : "";
  const filenameParts = [evalTabLabel, getFigureTitlePrefix(String(plotTabLabel).trim())]
    .filter((part) => part.length > 0)
    .map((part) => sanitizeFigureFilename(part));
  return `${filenameParts.join("-") || "figures"}.zip`;
}

function buildGroupedLegendModel(entries) {
  const seriesOrder = [];
  const seenSeries = new Set();
  const displayBySeries = new Map();

  for (const entry of entries) {
    for (const point of entry.points || []) {
      if (!seenSeries.has(point.series)) {
        seenSeries.add(point.series);
        seriesOrder.push(point.series);
      }
      if (!displayBySeries.has(point.series)) {
        displayBySeries.set(point.series, point.displaySeries || point.series);
      }
    }
  }

  const colorBySeries = new Map();
  const items = seriesOrder.map((series, index) => {
    const color = getBarColor(index);
    const label = displayBySeries.get(series) || series;
    colorBySeries.set(series, color);
    return { series, label, color };
  });

  return { seriesOrder, displayBySeries, colorBySeries, items };
}

function getLegendItemsForPoints(points, legendModel) {
  if (!legendModel) {
    return [];
  }
  const seriesInPoints = new Set(points.map((point) => point.series));
  return legendModel.items.filter((item) => seriesInPoints.has(item.series));
}

function createPlotLegendElement(legendItems) {
  const legend = document.createElement("div");
  legend.className = "plot-legend";
  legendItems.forEach((item) => {
    const legendItem = document.createElement("span");
    legendItem.className = "plot-legend-item";
    const swatch = document.createElement("span");
    swatch.className = "plot-legend-swatch";
    swatch.style.backgroundColor = item.color;
    const text = document.createElement("span");
    text.textContent = item.label;
    legendItem.appendChild(swatch);
    legendItem.appendChild(text);
    legend.appendChild(legendItem);
  });
  return legend;
}

function styleErrorBarSegment(line) {
  line.setAttribute("stroke", "currentColor");
  line.setAttribute("stroke-opacity", "0.78");
}

function getSvgExportViewBox(svg, width, height) {
  const viewBox = svg.getAttribute("viewBox");
  if (!viewBox) {
    return { minX: 0, minY: 0, width: Number(width), height: Number(height) };
  }
  const parts = viewBox
    .trim()
    .split(/\s+/)
    .map((part) => Number(part));
  if (parts.length !== 4 || parts.some((part) => !Number.isFinite(part))) {
    return { minX: 0, minY: 0, width: Number(width), height: Number(height) };
  }
  return { minX: parts[0], minY: parts[1], width: parts[2], height: parts[3] };
}

function resolveOpaqueExportBackgroundColor() {
  const candidates = [evalPlotContent, document.body, document.documentElement];
  for (const element of candidates) {
    if (!element) {
      continue;
    }
    const backgroundColor = getComputedStyle(element).backgroundColor;
    if (
      backgroundColor &&
      backgroundColor !== "transparent" &&
      backgroundColor !== "rgba(0, 0, 0, 0)"
    ) {
      return backgroundColor;
    }
  }
  return "#ffffff";
}

function prependExportBackgroundRect(svg, width, height, color = "#ffffff") {
  const box = getSvgExportViewBox(svg, width, height);
  const background = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  background.setAttribute("x", String(box.minX));
  background.setAttribute("y", String(box.minY));
  background.setAttribute("width", String(box.width));
  background.setAttribute("height", String(box.height));
  background.setAttribute("fill", color);
  svg.insertBefore(background, svg.firstChild);
}

function serializeLegendSvg(legendItems, options = {}) {
  if (!legendItems.length) {
    return "";
  }

  const fontSize = 12;
  const rowHeight = 22;
  const padding = 10;
  const swatchSize = 12;
  const textX = padding + swatchSize + 8;
  const computedStyle = getComputedStyle(evalPlotContent);
  const fontFamily = computedStyle.fontFamily || "Inter, Arial, sans-serif";
  const textColor = computedStyle.color || "#cbd5e1";

  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (context) {
    context.font = `${fontSize}px ${fontFamily}`;
  }
  const textWidths = legendItems.map((item) =>
    context ? context.measureText(item.label).width : item.label.length * (fontSize * 0.62)
  );
  const width = Math.ceil(
    Math.max(120, textX + Math.max(...textWidths, 0) + padding)
  );
  const height = padding * 2 + legendItems.length * rowHeight;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  svg.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  if (options.opaqueBackground) {
    prependExportBackgroundRect(svg, width, height, options.backgroundColor || resolveOpaqueExportBackgroundColor());
  }

  legendItems.forEach((item, index) => {
    const centerY = padding + index * rowHeight + rowHeight / 2;

    const swatch = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    swatch.setAttribute("x", String(padding));
    swatch.setAttribute("y", String(centerY - swatchSize / 2));
    swatch.setAttribute("width", String(swatchSize));
    swatch.setAttribute("height", String(swatchSize));
    swatch.setAttribute("rx", "2");
    swatch.setAttribute("fill", item.color);
    svg.appendChild(swatch);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", String(textX));
    text.setAttribute("y", String(centerY + fontSize / 3));
    text.setAttribute("fill", textColor);
    text.setAttribute("font-size", String(fontSize));
    text.setAttribute("font-family", fontFamily);
    text.textContent = item.label;
    svg.appendChild(text);
  });

  return `<?xml version="1.0" encoding="UTF-8"?>\n${new XMLSerializer().serializeToString(svg)}`;
}

function serializeSvgForDownload(sourceSvg, options = {}) {
  const clone = sourceSvg.cloneNode(true);
  const computedStyle = getComputedStyle(sourceSvg);
  const width = sourceSvg.getAttribute("width") || String(Math.ceil(sourceSvg.getBoundingClientRect().width));
  const height = sourceSvg.getAttribute("height") || String(Math.ceil(sourceSvg.getBoundingClientRect().height));

  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  clone.setAttribute("width", width);
  clone.setAttribute("height", height);
  if (!clone.hasAttribute("viewBox")) {
    clone.setAttribute("viewBox", `0 0 ${width} ${height}`);
  }
  if (options.opaqueBackground) {
    prependExportBackgroundRect(clone, width, height, options.backgroundColor || resolveOpaqueExportBackgroundColor());
  }
  clone.style.color = computedStyle.color;
  clone.style.fontFamily = computedStyle.fontFamily;
  clone.style.backgroundColor = computedStyle.backgroundColor;

  return `<?xml version="1.0" encoding="UTF-8"?>\n${new XMLSerializer().serializeToString(clone)}`;
}

function triggerBlobDownload(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function getZipDosDateTime(date = new Date()) {
  const year = Math.max(1980, date.getFullYear());
  return {
    time: ((date.getHours() & 0x1f) << 11) | ((date.getMinutes() & 0x3f) << 5) | ((Math.floor(date.getSeconds() / 2)) & 0x1f),
    date: (((year - 1980) & 0x7f) << 9) | (((date.getMonth() + 1) & 0x0f) << 5) | (date.getDate() & 0x1f),
  };
}

const crc32Table = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let value = i;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
    }
    table[i] = value >>> 0;
  }
  return table;
})();

function computeCrc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = crc32Table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function concatUint8Arrays(chunks) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return result;
}

function createZipBlob(files) {
  const encoder = new TextEncoder();
  const fileDate = getZipDosDateTime();
  const localChunks = [];
  const centralChunks = [];
  let offset = 0;

  for (const file of files) {
    const nameBytes = encoder.encode(file.name);
    const dataBytes = encoder.encode(file.content);
    const crc32 = computeCrc32(dataBytes);

    const localHeader = new Uint8Array(30 + nameBytes.length);
    const localView = new DataView(localHeader.buffer);
    localView.setUint32(0, 0x04034b50, true);
    localView.setUint16(4, 20, true);
    localView.setUint16(6, 0x0800, true);
    localView.setUint16(8, 0, true);
    localView.setUint16(10, fileDate.time, true);
    localView.setUint16(12, fileDate.date, true);
    localView.setUint32(14, crc32, true);
    localView.setUint32(18, dataBytes.length, true);
    localView.setUint32(22, dataBytes.length, true);
    localView.setUint16(26, nameBytes.length, true);
    localView.setUint16(28, 0, true);
    localHeader.set(nameBytes, 30);
    localChunks.push(localHeader, dataBytes);

    const centralHeader = new Uint8Array(46 + nameBytes.length);
    const centralView = new DataView(centralHeader.buffer);
    centralView.setUint32(0, 0x02014b50, true);
    centralView.setUint16(4, 20, true);
    centralView.setUint16(6, 20, true);
    centralView.setUint16(8, 0x0800, true);
    centralView.setUint16(10, 0, true);
    centralView.setUint16(12, fileDate.time, true);
    centralView.setUint16(14, fileDate.date, true);
    centralView.setUint32(16, crc32, true);
    centralView.setUint32(20, dataBytes.length, true);
    centralView.setUint32(24, dataBytes.length, true);
    centralView.setUint16(28, nameBytes.length, true);
    centralView.setUint16(30, 0, true);
    centralView.setUint16(32, 0, true);
    centralView.setUint16(34, 0, true);
    centralView.setUint16(36, 0, true);
    centralView.setUint32(38, 0, true);
    centralView.setUint32(42, offset, true);
    centralHeader.set(nameBytes, 46);
    centralChunks.push(centralHeader);

    offset += localHeader.length + dataBytes.length;
  }

  const centralDirectory = concatUint8Arrays(centralChunks);
  const endRecord = new Uint8Array(22);
  const endView = new DataView(endRecord.buffer);
  endView.setUint32(0, 0x06054b50, true);
  endView.setUint16(4, 0, true);
  endView.setUint16(6, 0, true);
  endView.setUint16(8, files.length, true);
  endView.setUint16(10, files.length, true);
  endView.setUint32(12, centralDirectory.length, true);
  endView.setUint32(16, offset, true);
  endView.setUint16(20, 0, true);

  const zipBytes = concatUint8Arrays([...localChunks, centralDirectory, endRecord]);
  return new Blob([zipBytes], { type: "application/zip" });
}

async function saveBlob(blob, suggestedName, types) {
  if (typeof window.showSaveFilePicker === "function") {
    try {
      const handle = await window.showSaveFilePicker({ suggestedName, types });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return true;
    } catch (error) {
      if (error && error.name === "AbortError") {
        return false;
      }
      console.warn("Save picker failed, falling back to browser download.", error);
    }
  }

  triggerBlobDownload(suggestedName, blob);
  return true;
}

function getVisiblePlotFigureCards() {
  return Array.from(evalPlotContent.querySelectorAll(".plot-card")).filter((card) => card.querySelector("svg"));
}

function updateDownloadFiguresButtonState() {
  renderDownloadFiguresButtonState(downloadFiguresButton, getVisiblePlotFigureCards().length);
}

async function downloadVisibleFigures() {
  const figureCards = getVisiblePlotFigureCards();
  if (!figureCards.length) {
    return;
  }

  const exportOptions = {
    opaqueBackground: state.exportOpaqueBackground,
    backgroundColor: state.exportOpaqueBackground ? resolveOpaqueExportBackgroundColor() : null,
  };
  const includeLegend = state.activePlotLegendItems.length > 1;
  const usedNames = new Set(includeLegend ? ["legend"] : []);
  const files = [];
  if (includeLegend) {
    files.push({
      filename: "legend.svg",
      content: serializeLegendSvg(state.activePlotLegendItems, exportOptions),
    });
  }

  figureCards.forEach((card, index) => {
    const svg = card.querySelector("svg");
    if (!svg) {
      return;
    }
    const title = card.querySelector(".plot-title")?.textContent?.trim() || `figure ${index + 1}`;
    files.push({
      filename: getUniqueFigureFilename(title, usedNames),
      content: serializeSvgForDownload(svg, exportOptions),
    });
  });

  if (!files.length) {
    return;
  }

  const zipBlob = createZipBlob(files.map((file) => ({ name: file.filename, content: file.content })));
  await saveBlob(
    zipBlob,
    getActivePlotTabZipFilename(),
    [{ description: "ZIP archive", accept: { "application/zip": [".zip"] } }]
  );
}

const evalPlotContentObserver = new MutationObserver(() => {
  updateDownloadFiguresButtonState();
});
evalPlotContentObserver.observe(evalPlotContent, { childList: true, subtree: true });
updateDownloadFiguresButtonState();

bindEvalJsonTabSelection({
  evaluationButton: evalJsonTabEvaluation,
  predictionButton: evalJsonTabPrediction,
  getActiveTab: () => state.activeEvalJsonTab,
  onSelect: (nextTab) => {
    state.activeEvalJsonTab = nextTab;
    renderEvaluations();
  },
});

initializeGitHubTokenInput(githubTokenInput);

folderInput.addEventListener("change", async (event) => {
  const files = Array.from(event.target.files || []);
  clearGitUrlQueryParam();
  await loadEvaluationsFromFiles(files);
  renderPredictions();
  renderEvaluations();
});

githubTokenInput.addEventListener("change", () => {
  persistGitHubTokenInputValue(githubTokenInput);
});

gitUrlInput.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  await handleGitLoadRequest();
});

loadGitButton.addEventListener("click", async () => {
  await handleGitLoadRequest();
});

function displayPredictionColumnName(column) {
  return stripPredictionFieldPrefix(column);
}

function displayEvalColumnName(column) {
  const normalizedColumn = stripEvaluationFieldPrefix(column);
  if (normalizedColumn.startsWith(JOB_RETURN_VALUE_PREFIX)) {
    return normalizedColumn.slice(JOB_RETURN_VALUE_PREFIX.length);
  }
  return normalizedColumn.replace(/^overrides\./, "");
}

function displayGroupFieldName(column) {
  if (
    column.startsWith(EVALUATION_PREFIX) ||
    column.startsWith(JOB_RETURN_VALUE_PREFIX) ||
    column.startsWith("overrides.")
  ) {
    return displayEvalColumnName(column);
  }
  return displayPredictionColumnName(column);
}

function getPlotDisplayLabel(label) {
  const text = String(label ?? "");
  return state.plotShortenLabels ? splitLabelByLastDot(text) : text;
}

function getPlotTitleLabel(plotEntry, metricType) {
  if (
    metricType === "F1MicroMultipleFieldsMetric" &&
    state.plotShortenLabels &&
    state.plotTabsBy === "suffix"
  ) {
    return plotEntry.prefix === "(root)" ? plotEntry.metricLabel : plotEntry.prefix;
  }
  return getPlotDisplayLabel(plotEntry.metricLabel);
}

function displayPlotGroupFieldName(column) {
  return getPlotDisplayLabel(displayGroupFieldName(column));
}

function getDefaultTruncateColumns(predictionColumns) {
  return selectors.getDefaultTruncateColumns(predictionColumns);
}

/**
 * Choose default prediction group-by fields from varying non-seed override columns.
 */
function getDefaultGroupByFields(predictionColumns, predictionViews = getPredictionViews()) {
  return selectors.getDefaultGroupByFields(predictionColumns, predictionViews);
}

function getDefaultEvalGroupByFields(evalColumns, evaluations = []) {
  return selectors.getDefaultEvalGroupByFields(evalColumns, evaluations);
}

function getDefaultEvalTruncateColumns() {
  return new Set();
}

function setConfiguredDefault(defaults, column, value) {
  const nextValue = String(value ?? "");
  if (nextValue.trim() === "") {
    delete defaults[column];
  } else {
    defaults[column] = nextValue;
  }
}

function getPredictionDefaultValue(column) {
  return selectors.getPredictionDefaultValue(state, column);
}

function getPredictionEffectiveValue(predictionFlat, column) {
  return selectors.getPredictionEffectiveValue(state, predictionFlat, column);
}

/**
 * Build a stable signature from the effective prediction values for the provided columns.
 */
function getPredictionEffectiveSignature(
  predictionFlat,
  predictionColumns = getCurrentPredictionColumns()
) {
  return selectors.getPredictionEffectiveSignature(state, predictionFlat, predictionColumns);
}

function getEvalDefaultValue(evalTabState, column) {
  return selectors.getEvalDefaultValue(evalTabState, column);
}

/**
 * Return prediction columns whose selected prediction views still contain missing values.
 */
function getPredictionColumnsWithMissingValues(
  predictionViews,
  predictionColumns = getCurrentPredictionColumns(predictionViews)
) {
  return selectors.getPredictionColumnsWithMissingValues(state, predictionViews, predictionColumns);
}

/**
 * Collect non-empty suggestion values for a prediction column from the current prediction views.
 */
function getPredictionDefaultSuggestions(predictionViews, column) {
  return selectors.getPredictionDefaultSuggestions(predictionViews, column);
}

/**
 * Count how many prediction views are missing a value for the given prediction column.
 */
function getPredictionMissingValueCount(predictionViews, column) {
  return selectors.getPredictionMissingValueCount(predictionViews, column);
}

function getEvalColumnsWithMissingValues(evaluations, evalColumns) {
  return selectors.getEvalColumnsWithMissingValues(evaluations, evalColumns);
}

function getEvalDefaultSuggestions(evaluations, column) {
  return selectors.getEvalDefaultSuggestions(evaluations, column);
}

function getEvalMissingValueCount(evaluations, column) {
  return selectors.getEvalMissingValueCount(evaluations, column);
}


function setGroupByFields(columns) {
  state.groupByFields = [...columns];
  renderPredictions();
  renderEvaluations();
}


function getEvalColumnSections(evalColumns) {
  const overrides = evalColumns.filter((column) => !isJobReturnValueColumn(column)).sort();
  const jobReturnValueColumns = evalColumns.filter((column) => isJobReturnValueColumn(column)).sort();
  return [
    { label: "overrides", columns: overrides },
    { label: "job_return_value", columns: jobReturnValueColumns },
  ].filter((section) => section.columns.length > 0);
}

/**
 * Return the evaluation columns for the currently active evaluation experiment.
 */
function getActiveEvalColumns() {
  return selectors.getActiveEvalColumns(state);
}

function setActiveEvalGroupByFields(columns) {
  if (!state.activeEvalTab) {
    return;
  }
  const evalColumns = getActiveEvalColumns();
  const evalTabState = ensureEvalTabState(state.activeEvalTab, evalColumns);
  const validColumns = new Set(evalColumns);
  evalTabState.groupByFields = [...new Set(columns)].filter((column) => validColumns.has(column));
  renderEvaluations();
}

function ensureEvalTabState(
  experiment,
  evalColumns,
  evaluations = getSelectedEvaluationsForExperiment(experiment)
) {
  return dashboardStore.ensureEvalTabState(state, experiment, evalColumns, {
    evaluations,
    getDefaultEvalGroupByFields,
    getDefaultEvalTruncateColumns,
  });
}

/**
 * Synchronize selected group ids with the current valid group-id set while preserving
 * still-valid selections and auto-selecting newly introduced groups.
 */
function syncSelectedGroupIds(selectionState, validGroupIds) {
  dashboardStore.syncSelectedGroupIds(selectionState, validGroupIds);
}

groupByAllButton.addEventListener("click", () => {
  setGroupByFields(getCurrentPredictionColumns());
});

groupByNoneButton.addEventListener("click", () => {
  setGroupByFields([]);
});

groupByToggleButton.addEventListener("click", () => {
  const predictionColumns = getCurrentPredictionColumns();
  const nextGroupByFields = getToggleOnlyColumns(predictionColumns, state.groupByFields);
  setGroupByFields(nextGroupByFields);
});

evalGroupByAllButton.addEventListener("click", () => {
  setActiveEvalGroupByFields(getActiveEvalColumns());
});

evalGroupByNoneButton.addEventListener("click", () => {
  setActiveEvalGroupByFields([]);
});

evalGroupByToggleButton.addEventListener("click", () => {
  if (!state.activeEvalTab) {
    return;
  }
  const evalColumns = getActiveEvalColumns();
  const evalTabState = ensureEvalTabState(state.activeEvalTab, evalColumns);
  const nextGroupByFields = getToggleOnlyColumns(evalColumns, evalTabState.groupByFields);
  setActiveEvalGroupByFields(nextGroupByFields);
});

predictionResetSortButton.addEventListener("click", () => {
  if (!normalizeSortConfig(state.predictionSort).length) {
    return;
  }
  state.predictionSort = [];
  renderPredictions();
});

evalResetSortButton.addEventListener("click", () => {
  if (!state.activeEvalTab) {
    return;
  }
  const evalTabState = ensureEvalTabState(state.activeEvalTab, getActiveEvalColumns());
  if (!normalizeSortConfig(evalTabState.sort).length) {
    return;
  }
  evalTabState.sort = [];
  renderEvaluations();
});

bindDelegatedTabSelection({
  containerElement: optionsTabs,
  getActiveValue: () => state.activeOptionsTab,
  onSelect: (tab) => {
    state.activeOptionsTab = tab;
    renderStaticTabState({
      buttonElements: optionsTabButtons,
      panelElements: optionsTabPanels,
      activeValue: state.activeOptionsTab,
    });
  },
});

bindDelegatedTabSelection({
  containerElement: evalOptionsTabs,
  getActiveValue: () => {
    if (!state.activeEvalTab || !state.evalTabStates[state.activeEvalTab]) {
      return null;
    }
    return state.evalTabStates[state.activeEvalTab].activeOptionsTab;
  },
  onSelect: (tab) => {
    if (!state.activeEvalTab || !state.evalTabStates[state.activeEvalTab]) {
      return;
    }
    state.evalTabStates[state.activeEvalTab].activeOptionsTab = tab;
    renderStaticTabState({
      buttonElements: evalOptionsTabButtons,
      panelElements: evalOptionsTabPanels,
      activeValue: state.evalTabStates[state.activeEvalTab].activeOptionsTab,
      buttonAttribute: "data-eval-tab",
      panelAttribute: "data-eval-tab-panel",
    });
  },
  valueAttribute: "data-eval-tab",
});

truncateDefaultsButton.addEventListener("click", () => {
  state.truncateEnabledColumns = getDefaultTruncateColumns(getCurrentPredictionColumns());
  renderPredictions();
})

plotShortenLabels.addEventListener("change", () => {
  state.plotShortenLabels = plotShortenLabels.checked;
  renderEvaluations();
});

plotRoundingPrecision.addEventListener("change", () => {
  const parsed = Number.parseInt(plotRoundingPrecision.value, 10);
  const clamped = Number.isFinite(parsed) ? Math.max(0, Math.min(6, parsed)) : 2;
  state.plotRoundingPrecision = clamped;
  plotRoundingPrecision.value = String(clamped);
  renderEvaluations();
});

plotConfusionMinLabelTotal.addEventListener("change", () => {
  const parsed = Number.parseInt(plotConfusionMinLabelTotal.value, 10);
  const clamped = Number.isFinite(parsed) ? Math.max(0, parsed) : 3;
  state.plotConfusionMinLabelTotal = clamped;
  plotConfusionMinLabelTotal.value = String(clamped);
  renderEvaluations();
});

plotTpFpFnMinLabelTotal.addEventListener("change", () => {
  const parsed = Number.parseInt(plotTpFpFnMinLabelTotal.value, 10);
  const clamped = Number.isFinite(parsed) ? Math.max(0, parsed) : 3;
  state.plotTpFpFnMinLabelTotal = clamped;
  plotTpFpFnMinLabelTotal.value = String(clamped);
  renderEvaluations();
});

plotTpFpFnMinDocumentTotal.addEventListener("change", () => {
  const parsed = Number.parseInt(plotTpFpFnMinDocumentTotal.value, 10);
  const clamped = Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
  state.plotTpFpFnMinDocumentTotal = clamped;
  plotTpFpFnMinDocumentTotal.value = String(clamped);
  renderEvaluations();
});

plotShowLegendOnce.addEventListener("change", () => {
  state.plotShowLegendOnce = plotShowLegendOnce.checked;
  renderEvaluations();
});

exportOpaqueBackground.addEventListener("change", () => {
  state.exportOpaqueBackground = exportOpaqueBackground.checked;
  renderPlotControls({
    metricType: getMetricTypeForEvaluationContext(state.activeEvalTab || ""),
    plotTabsBy: state.plotTabsBy,
    confusionTabsBy: state.confusionTabsBy,
    plotShortenLabels: state.plotShortenLabels,
    plotRoundingPrecision: state.plotRoundingPrecision,
    plotConfusionMinLabelTotal: state.plotConfusionMinLabelTotal,
    plotTpFpFnMinLabelTotal: state.plotTpFpFnMinLabelTotal,
    plotTpFpFnMinDocumentTotal: state.plotTpFpFnMinDocumentTotal,
    plotShowLegendOnce: state.plotShowLegendOnce,
    exportOpaqueBackground: state.exportOpaqueBackground,
    plotTabsByPrefixButton,
    plotTabsBySuffixButton,
    confusionTabsByMetricFieldButton,
    confusionTabsByPredictionGroupButton,
    plotShortenLabelsInput: plotShortenLabels,
    plotRoundingPrecisionInput: plotRoundingPrecision,
    plotConfusionMinLabelTotalRow,
    plotConfusionMinLabelTotalInput: plotConfusionMinLabelTotal,
    plotTpFpFnMinLabelTotalRow,
    plotTpFpFnMinLabelTotalInput: plotTpFpFnMinLabelTotal,
    plotTpFpFnMinDocumentTotalRow,
    plotTpFpFnMinDocumentTotalInput: plotTpFpFnMinDocumentTotal,
    plotTabsByRow,
    plotConfusionTabsByRow,
    plotGroupBarsRow,
    plotShowLegendOnceRow,
    plotShowLegendOnceInput: plotShowLegendOnce,
    exportOpaqueBackgroundInput: exportOpaqueBackground,
  });
});

downloadFiguresButton.addEventListener("click", async () => {
  if (downloadFiguresButton.disabled) {
    return;
  }
  setDownloadFiguresButtonBusy(downloadFiguresButton);
  try {
    await downloadVisibleFigures();
  } finally {
    updateDownloadFiguresButtonState();
  }
});

plotTabsByPrefixButton.addEventListener("click", () => {
  if (state.plotTabsBy === "prefix") {
    return;
  }
  state.plotTabsBy = "prefix";
  state.activeEvalPlotTab = null;
  renderEvaluations();
});

plotTabsBySuffixButton.addEventListener("click", () => {
  if (state.plotTabsBy === "suffix") {
    return;
  }
  state.plotTabsBy = "suffix";
  state.activeEvalPlotTab = null;
  renderEvaluations();
});

confusionTabsByMetricFieldButton.addEventListener("click", () => {
  if (state.confusionTabsBy === "metric_field") {
    return;
  }
  state.confusionTabsBy = "metric_field";
  state.activeEvalPlotTab = null;
  renderEvaluations();
});

confusionTabsByPredictionGroupButton.addEventListener("click", () => {
  if (state.confusionTabsBy === "prediction_group") {
    return;
  }
  state.confusionTabsBy = "prediction_group";
  state.activeEvalPlotTab = null;
  renderEvaluations();
});

/**
 * Split current prediction columns into UI sections for rendering the prediction table header.
 */
function getPredictionColumnSections(predictionColumns = getCurrentPredictionColumns()) {
  const jobReturnValueColumns = predictionColumns
    .filter((column) => column.startsWith(PREDICTION_JOB_RETURN_VALUE_PREFIX))
    .sort();
  const overrideColumns = predictionColumns
    .filter((column) => column.startsWith(PREDICTION_OVERRIDES_PREFIX))
    .sort();
  const otherColumns = predictionColumns
    .filter(
      (column) =>
        !column.startsWith(PREDICTION_JOB_RETURN_VALUE_PREFIX) &&
        !column.startsWith(PREDICTION_OVERRIDES_PREFIX)
    )
    .sort();
  return [
    { label: "overrides", columns: overrideColumns },
    { label: "job_return_value", columns: jobReturnValueColumns },
    { label: "other", columns: otherColumns },
  ].filter((section) => section.columns.length > 0);
}

function formatDistinctValueDisplay(values) {
  if (values.size <= 1) {
    return values.values().next().value || "";
  }
  return `(mixed: ${values.size} values)`;
}


function setPredictionSort(column, event = {}) {
  state.predictionSort = getNextSortConfig(state.predictionSort, column, { append: event.shiftKey });
  renderPredictions();
}

function setEvalSort(column, event = {}) {
  if (!state.activeEvalTab) {
    return;
  }
  const evalTabState = ensureEvalTabState(state.activeEvalTab, getActiveEvalColumns());
  evalTabState.sort = getNextSortConfig(evalTabState.sort, column, { append: event.shiftKey });
  renderEvaluations();
}

/**
 * Reset load-dependent UI state after new canonical prediction/evaluation data is imported.
 * All prediction/evaluation structures remain selector-derived and are not stored here.
 */
function resetDerivedUiStateAfterLoad() {
  const predictionViews = getPredictionViews();
  const predictionColumns = getCurrentPredictionColumns(predictionViews);
  const nextGroupByFields = getDefaultGroupByFields(predictionColumns, predictionViews);
  dashboardStore.resetDerivedUiStateAfterLoad(state, {
    predictionViews,
    predictionColumns,
    predictionGroups: getPredictionGroups(predictionViews, nextGroupByFields, predictionColumns),
    getDefaultGroupByFields,
    getDefaultTruncateColumns,
  });
}

function updateLoadStatusSummary({ candidateRunDirs, loadedCount, skippedDuplicate, skippedPredictRuns, skippedMissingJob, skippedUnsupportedVersion, skippedInvalid, skippedMissingPredictionId, skippedConflictingPredictionId }) {
  renderLoadStatusSummary(dom, {
    loadedSources: Array.from(state.loadedFolders).sort(),
    totalEvaluations: state.evaluations.length,
    candidateRunDirs,
    loadedCount,
    skippedDuplicate,
    skippedPredictRuns,
    skippedMissingJob,
    skippedUnsupportedVersion,
    skippedInvalid,
    skippedMissingPredictionId,
    skippedConflictingPredictionId,
  });
}

/**
 * Apply a shared-ingestion result to canonical dashboard state and refresh derived UI state.
 *
 * @param {string} sourceLabel - Loaded source label.
 * @param {{predictionAdditions: Record<string, object>, evaluationAdditions: Array<object>, failures: Array<{runDir: string, error: Error}>, summary: object}} ingestionResult - Shared ingestion result.
 */
function applyIngestionResult(sourceLabel, ingestionResult) {
  state.loadedFolders.add(sourceLabel);
  for (const { runDir, error } of ingestionResult.failures) {
    console.error(`Failed to parse run at ${runDir}`, error);
  }
  for (const [predictionId, prediction] of Object.entries(ingestionResult.predictionAdditions)) {
    state.predictions[predictionId] = prediction;
  }
  state.evaluations.push(...ingestionResult.evaluationAdditions);
  resetDerivedUiStateAfterLoad();
  updateLoadStatusSummary(ingestionResult.summary);
}

// Load only single evaluation runs: any selected folder tree can contribute evaluations as long as a run
// directory contains both job_return_value.json and .hydra/overrides.yaml. predict runs are excluded,
// while prediction payloads are canonicalized separately and linked via predictionId.
async function loadEvaluationsFromEntries(entries, rootLabel) {
  if (!entries.length) {
    renderLoadStatusStage(dom, `No relevant run files found in ${rootLabel}.`);
    return;
  }

  applyIngestionResult(rootLabel, ingestRunEntries(entries, {
    existingPredictions: state.predictions,
    existingEvaluations: state.evaluations,
  }));
}

async function loadEvaluationsFromFiles(files) {
  hideLoadProgress();
  if (!files.length) {
    renderLoadStatusStage(dom, "No files selected.");
    return;
  }

  const { rootLabel, entries } = await collectLocalEvaluationEntries(files);
  await loadEvaluationsFromEntries(entries, rootLabel);
}

function updateLoadStatusStage(title, details = []) {
  renderLoadStatusStage(dom, title, details);
}

function hideLoadProgress() {
  clearLoadProgress(dom);
}

function setLoadProgress({ completedFiles = 0, totalFiles = 0, completedBytes = 0, totalBytes = 0, label = "" } = {}) {
  renderLoadProgress(dom, { completedFiles, totalFiles, completedBytes, totalBytes, label });
}

async function loadEvaluationsFromGitUrl(rawUrl) {
  const trimmedUrl = String(rawUrl || "").trim();
  if (!trimmedUrl) {
    hideLoadProgress();
    renderLoadStatusStage(dom, "Enter a GitHub tree URL first.");
    return;
  }

  const token = persistGitHubTokenInputValue(githubTokenInput);
  hideLoadProgress();
  const gitLoadResult = await loadGitHubEntriesFromTreeUrl(trimmedUrl, {
    token,
    onStatus: ({ title, details }) => updateLoadStatusStage(title, details),
    onProgress: (progress) => setLoadProgress(progress),
  });
  if (!gitLoadResult.files.length) {
    hideLoadProgress();
    renderLoadStatusStage(dom, `No matching run files found in ${gitLoadResult.sourceLabel}.`);
    return;
  }

  updateLoadStatusStage("Loading evaluation runs from GitHub files", [
    gitLoadResult.sourceLabel,
    `Fetched files: ${gitLoadResult.entries.length}`,
  ]);
  await loadEvaluationsFromEntries(gitLoadResult.entries, gitLoadResult.sourceLabel);
  setLoadProgress({
    completedFiles: gitLoadResult.files.length,
    totalFiles: gitLoadResult.files.length,
    completedBytes: gitLoadResult.totalBytes,
    totalBytes: gitLoadResult.totalBytes,
    label: "GitHub fetch complete",
  });
}

async function handleGitLoadRequest() {
  const trimmedUrl = String(gitUrlInput.value || "").trim();
  if (!trimmedUrl) {
    renderLoadStatusStage(dom, "Enter a GitHub tree URL first.");
    return;
  }

  loadGitButton.disabled = true;
  setGitUrlQueryParam(trimmedUrl);
  try {
    await loadEvaluationsFromGitUrl(trimmedUrl);
    renderPredictions();
    renderEvaluations();
  } catch (error) {
    console.error(error);
    renderLoadStatusStage(dom, `GitHub load failed: ${error.message || error}`);
  } finally {
    loadGitButton.disabled = false;
  }
}

async function initializeGitUrlFromQueryParam() {
  await runGitUrlQueryParamBootstrap({
    inputElement: gitUrlInput,
    onLoadRequested: () => handleGitLoadRequest(),
  });
}

void initializeGitUrlFromQueryParam();

function getPredictionGroupSortValue(group, column) {
  return selectors.getPredictionGroupSortValue(state, group, column);
}

function getPredictionMemberSortValue(predictionView, column) {
  return selectors.getPredictionMemberSortValue(state, predictionView, column);
}

/**
 * Return prediction groups sorted according to the active prediction sort config.
 */
function getSortedPredictionGroups(predictionGroups = getCurrentPredictionGroups()) {
  return selectors.getSortedPredictionGroups(state, predictionGroups);
}

function getSortedPredictionMembers(predictions) {
  return selectors.getSortedPredictionMembers(state, predictions);
}

function setSelectedGroupIds(groupIds) {
  state.selectedGroupIds = new Set(groupIds);
  renderPredictions();
  renderEvaluations();
}


window.addEventListener("resize", () => {
  updateStickyControlColumnOffsets(predictionsTable);
  updateStickyControlColumnOffsets(evaluationsTable);
});

function getGroupValueDisplay(group, column) {
  return selectors.getGroupValueDisplay(state, group, column);
}

/**
 * Render the Predictions table from derived prediction views and prediction groups.
 */
function renderPredictions() {
  const predictionViews = getPredictionViews();
  const predictionGroups = getCurrentPredictionGroups();

  predictionsTable.innerHTML = "";
  predictionDefaultsList.innerHTML = "";
  state.predictionSort = renderSortStatus({
    labelElement: predictionSortedByLabel,
    resetButton: predictionResetSortButton,
    sortConfig: state.predictionSort,
    validColumns: [...SORTABLE_CONTROL_COLUMNS, ...getCurrentPredictionColumns()],
    displayColumnName: displayPredictionColumnName,
  });
  if (!predictionGroups.length) {
    renderGroupByButtonState(
      {
        allButton: groupByAllButton,
        toggleButton: groupByToggleButton,
        noneButton: groupByNoneButton,
      },
      []
    );
    setPanelVisibility(predictionDefaultsPanel, false);
    predictionSummary.textContent = "No predictions found. Load a folder containing evaluate run outputs.";
    return;
  }

  predictionSummary.textContent =
    `Predictions: ${predictionViews.length} | Groups: ${predictionGroups.length} | Group-by: ` +
    (state.groupByFields.length
      ? state.groupByFields.map((field) => displayPredictionColumnName(field)).join(", ")
      : "(none; one row per unique prediction)");

  const predictionSections = getPredictionColumnSections();
  const orderedPredictionColumns = predictionSections.flatMap((section) => section.columns);
  renderGroupByButtonState(
    {
      allButton: groupByAllButton,
      toggleButton: groupByToggleButton,
      noneButton: groupByNoneButton,
    },
    orderedPredictionColumns
  );
  renderStaticTabState({
    buttonElements: optionsTabButtons,
    panelElements: optionsTabPanels,
    activeValue: state.activeOptionsTab,
  });
  const selectedPredictionViews = getSelectedPredictionViews();
  const predictionDefaultColumns = getPredictionColumnsWithMissingValues(
    selectedPredictionViews,
    orderedPredictionColumns
  );
  renderOptionsPanel({
    documentLike: document,
    checkboxListElement: truncateColumnsList,
    checkboxColumns: orderedPredictionColumns,
    checkedValues: state.truncateEnabledColumns,
    getCheckboxLabel: displayPredictionColumnName,
    onCheckboxToggle: (column, checked) => {
      if (checked) {
        state.truncateEnabledColumns.add(column);
      } else {
        state.truncateEnabledColumns.delete(column);
      }
      renderPredictions();
    },
    defaultsListElement: predictionDefaultsList,
    defaultsPanelElement: predictionDefaultsPanel,
    defaultColumns: predictionDefaultColumns,
    getDefaultLabel: displayPredictionColumnName,
    getDefaultValue: getPredictionDefaultValue,
    getDefaultSuggestions: (column) => getPredictionDefaultSuggestions(selectedPredictionViews, column),
    getDefaultMissingCount: (column) =>
      getPredictionMissingValueCount(selectedPredictionViews, column),
    inputIdPrefix: "prediction-default",
    onDefaultCommit: (column, nextValue) => {
      setConfiguredDefault(state.predictionDefaultValues, column, nextValue);
      renderPredictions();
      renderEvaluations();
    },
  });
  const displayedGroups = getSortedPredictionGroups(predictionGroups);

  renderPredictionTable({
    documentLike: document,
    tableElement: predictionsTable,
    predictionSections,
    orderedPredictionColumns,
    displayedGroups,
    predictionSort: state.predictionSort,
    truncateEnabledColumns: state.truncateEnabledColumns,
    groupByFields: state.groupByFields,
    selectedGroupIds: state.selectedGroupIds,
    expandedGroupIds: state.expandedGroupIds,
    displayColumnName: displayPredictionColumnName,
    onSortToggle: setPredictionSort,
    onToggleGroupByColumn: (column, checked) => {
      const nextGroupByFields = new Set(state.groupByFields);
      if (checked) {
        nextGroupByFields.add(column);
      } else {
        nextGroupByFields.delete(column);
      }
      setGroupByFields(nextGroupByFields);
    },
    onToggleGroupExpansion: (groupId) => {
      if (state.expandedGroupIds.has(groupId)) {
        state.expandedGroupIds.delete(groupId);
      } else {
        state.expandedGroupIds.add(groupId);
      }
      renderPredictions();
    },
    onToggleGroupSelection: (groupId, checked) => {
      const nextSelectedGroupIds = new Set(state.selectedGroupIds);
      if (checked) {
        nextSelectedGroupIds.add(groupId);
      } else {
        nextSelectedGroupIds.delete(groupId);
      }
      setSelectedGroupIds(nextSelectedGroupIds);
    },
    onSelectAllDisplayed: (checked, displayedGroupIds) => {
      setSelectedGroupIds(checked ? displayedGroupIds : []);
    },
    getGroupValueDisplay,
    getSortedPredictionMembers,
    getPredictionEffectiveValue,
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });
  updateStickyControlColumnOffsets(predictionsTable);
}

/**
 * Group evaluations by the active prediction and evaluation grouping fields.
 * The returned group shape matches the current evaluation table/rendering expectations.
 */
function getEvaluationGroups(
  evaluations,
  groupByFields,
  predictionGroupByFields = state.groupByFields,
  evalTabState = state.activeEvalTab ? state.evalTabStates[state.activeEvalTab] : null
) {
  return selectors.getEvaluationGroups(state, evaluations, groupByFields, predictionGroupByFields, evalTabState);
}

function getEvaluationGroupSortValue(group, column, evalTabState) {
  return selectors.getEvaluationGroupSortValue(group, column, evalTabState);
}

function getEvaluationRunSortValue(evaluation, column, evalTabState) {
  return selectors.getEvaluationRunSortValue(evaluation, column, evalTabState);
}

function getSortedEvaluationGroups(groups, evalTabState) {
  return selectors.getSortedEvaluationGroups(groups, evalTabState);
}

function getSortedEvaluations(evaluations, evalTabState) {
  return selectors.getSortedEvaluations(evaluations, evalTabState);
}

/**
 * Synchronize evaluation-group UI state with the currently derived evaluation groups
 * and experiment evaluations.
 */
function syncEvaluationGroupUiState(evalTabState, evaluationGroups, experimentEvaluations) {
  dashboardStore.syncEvaluationGroupUiState(evalTabState, evaluationGroups, experimentEvaluations);
}

/**
 * Return the current evaluation context derived from canonical state and current evaluation UI settings.
 */
function getEvaluationContext(
  activeExperiment = state.activeEvalTab,
  selectedEvaluations = gatherSelectedEvaluations()
) {
  return selectors.getEvaluationContext(state, activeExperiment, selectedEvaluations);
}

/**
 * Filter evaluation groups down to the currently selected evaluation group ids.
 */
function getSelectedEvaluationGroups(evaluationContext = getEvaluationContext()) {
  return selectors.getSelectedEvaluationGroups(state, evaluationContext);
}

function getGroupValueDisplayFromEvaluations(evaluations, getter) {
  return selectors.getGroupValueDisplayFromEvaluations(evaluations, getter);
}

function getVaryingFields(groups, fields) {
  if (!fields.length || groups.length <= 1) {
    return [];
  }
  return fields.filter((field) => {
    const values = new Set(groups.map((group) => normalizeValue(group.values?.[field])));
    return values.size > 1;
  });
}


function getGroupLabelForFields(group, labelFields, fallback, fieldNameFormatter = displayGroupFieldName) {
  if (labelFields.length === 0) {
    return fallback;
  }
  return labelFields
    .map(
      (field) =>
        `${fieldNameFormatter(field)}=${normalizeValue(group.values[field])}`
    )
    .join(" | ");
}

/**
 * Combine prediction grouping and evaluation grouping into the plot-group shape
 * consumed by plot and confusion-matrix rendering.
 */
function getPlotGroups(activeExperiment, selectedEvalGroups, evalGroupByFields, evalTabState) {
  return selectors.getPlotGroups(state, activeExperiment, selectedEvalGroups, evalGroupByFields, evalTabState);
}

function getBarColor(index) {
  const palette = [
    "#60a5fa",
    "#f97316",
    "#22c55e",
    "#a78bfa",
    "#f43f5e",
    "#14b8a6",
    "#eab308",
    "#8b5cf6",
    "#06b6d4",
    "#ef4444",
  ];
  return palette[index % palette.length];
}

function fitSvgToContents(svg, contentGroup, minWidth, minHeight) {
  if (!svg.isConnected) {
    return false;
  }
  let bbox;
  try {
    bbox = contentGroup.getBBox();
  } catch (error) {
    return false;
  }
  if (
    !bbox ||
    !Number.isFinite(bbox.x) ||
    !Number.isFinite(bbox.y) ||
    !Number.isFinite(bbox.width) ||
    !Number.isFinite(bbox.height)
  ) {
    return false;
  }

  const padding = 8;
  const shiftX = Math.max(0, padding - bbox.x);
  const shiftY = Math.max(0, padding - bbox.y);
  contentGroup.setAttribute("transform", `translate(${shiftX}, ${shiftY})`);

  const fittedWidth = Math.ceil(
    Math.max(minWidth + shiftX, bbox.x + bbox.width + shiftX + padding)
  );
  const fittedHeight = Math.ceil(
    Math.max(minHeight + shiftY, bbox.y + bbox.height + shiftY + padding)
  );

  svg.setAttribute("width", String(fittedWidth));
  svg.setAttribute("height", String(fittedHeight));
  svg.setAttribute("viewBox", `0 0 ${fittedWidth} ${fittedHeight}`);
  return true;
}

function scheduleAdaptiveSvgFit(svg, contentGroup, minWidth, minHeight) {
  let attempts = 4;
  const runFit = () => {
    const fitted = fitSvgToContents(svg, contentGroup, minWidth, minHeight);
    if (!fitted && attempts > 0) {
      attempts -= 1;
      requestAnimationFrame(runFit);
    }
  };

  requestAnimationFrame(runFit);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready
      .then(() => {
        requestAnimationFrame(runFit);
      })
      .catch(() => {});
  }
}

function createBarPlotSvg(points) {
  const width = Math.max(720, points.length * 150);
  const height = 320;
  const margin = { top: 18, right: 20, bottom: 95, left: 60 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const yMax = Math.max(
    0.05,
    ...points.map((point) => point.mean + point.std)
  );
  const step = chartWidth / Math.max(points.length, 1);
  const barWidth = Math.max(20, Math.min(60, step * 0.55));

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const contentGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(contentGroup);

  const yTicks = 5;
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const value = (yMax * tick) / yTicks;
    const y = margin.top + chartHeight - (value / yMax) * chartHeight;
    const grid = document.createElementNS("http://www.w3.org/2000/svg", "line");
    grid.setAttribute("x1", String(margin.left));
    grid.setAttribute("x2", String(width - margin.right));
    grid.setAttribute("y1", String(y));
    grid.setAttribute("y2", String(y));
    grid.setAttribute("stroke", "#64748b66");
    grid.setAttribute("stroke-width", "1");
    contentGroup.appendChild(grid);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 8));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = value.toFixed(2);
    contentGroup.appendChild(label);
  }

  for (const [index, point] of points.entries()) {
    const centerX = margin.left + step * index + step / 2;
    const barHeight = (point.mean / yMax) * chartHeight;
    const barY = margin.top + chartHeight - barHeight;
    const barX = centerX - barWidth / 2;

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", String(barX));
    rect.setAttribute("y", String(barY));
    rect.setAttribute("width", String(barWidth));
    rect.setAttribute("height", String(Math.max(0, barHeight)));
    rect.setAttribute("fill", "#60a5fa");
    rect.style.cursor = "crosshair";
    rect.addEventListener("mouseover", (event) => {
      showBarTooltip(event, [
        point.label,
        `mean: ${Number(point.mean).toFixed(4)}`,
        `std:  ${Number(point.std).toFixed(4)}`,
      ]);
    });
    rect.addEventListener("mousemove", positionBarTooltip);
    rect.addEventListener("mouseout", hideBarTooltip);
    contentGroup.appendChild(rect);

    const errTop = margin.top + chartHeight - ((point.mean + point.std) / yMax) * chartHeight;
    const errBottom = margin.top + chartHeight - ((point.mean - point.std) / yMax) * chartHeight;
    const errorLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    errorLine.setAttribute("x1", String(centerX));
    errorLine.setAttribute("x2", String(centerX));
    errorLine.setAttribute("y1", String(errTop));
    errorLine.setAttribute("y2", String(errBottom));
    styleErrorBarSegment(errorLine);
    errorLine.setAttribute("stroke-width", "2");
    contentGroup.appendChild(errorLine);

    const capTop = document.createElementNS("http://www.w3.org/2000/svg", "line");
    capTop.setAttribute("x1", String(centerX - 6));
    capTop.setAttribute("x2", String(centerX + 6));
    capTop.setAttribute("y1", String(errTop));
    capTop.setAttribute("y2", String(errTop));
    styleErrorBarSegment(capTop);
    capTop.setAttribute("stroke-width", "2");
    contentGroup.appendChild(capTop);

    const capBottom = document.createElementNS("http://www.w3.org/2000/svg", "line");
    capBottom.setAttribute("x1", String(centerX - 6));
    capBottom.setAttribute("x2", String(centerX + 6));
    capBottom.setAttribute("y1", String(errBottom));
    capBottom.setAttribute("y2", String(errBottom));
    styleErrorBarSegment(capBottom);
    capBottom.setAttribute("stroke-width", "2");
    contentGroup.appendChild(capBottom);

    const xLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
    xLabel.setAttribute("x", String(centerX));
    xLabel.setAttribute("y", String(height - margin.bottom + 16));
    xLabel.setAttribute("transform", `rotate(-28 ${centerX} ${height - margin.bottom + 16})`);
    xLabel.setAttribute("text-anchor", "end");
    xLabel.setAttribute("fill", "currentColor");
    xLabel.setAttribute("font-size", "11");
    xLabel.textContent = point.displayLabel;
    contentGroup.appendChild(xLabel);
  }

  scheduleAdaptiveSvgFit(svg, contentGroup, width, height);
  return svg;
}

function createGroupedBarPlotSvg(points, legendModel = null) {
  const categoryOrder = [];
  const categorySet = new Set();
  const categoryDisplayMap = new Map();
  const valueMap = new Map();

  for (const point of points) {
    if (!categorySet.has(point.category)) {
      categorySet.add(point.category);
      categoryOrder.push(point.category);
    }
    if (!categoryDisplayMap.has(point.category)) {
      categoryDisplayMap.set(point.category, point.displayCategory);
    }
    valueMap.set(`${point.category}|#|${point.series}`, point);
  }

  const localSeriesOrder = [];
  const localSeriesSet = new Set();
  for (const point of points) {
    if (!localSeriesSet.has(point.series)) {
      localSeriesSet.add(point.series);
      localSeriesOrder.push(point.series);
    }
  }

  const seriesOrder = legendModel?.seriesOrder?.length ? legendModel.seriesOrder : localSeriesOrder;

  const seriesCount = Math.max(1, seriesOrder.length);
  const width = Math.max(760, categoryOrder.length * (120 + seriesCount * 26));
  const height = 340;
  const margin = { top: 18, right: 20, bottom: 95, left: 60 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const yMax = Math.max(
    0.05,
    ...points.map((point) => point.mean + point.std)
  );
  const categoryStep = chartWidth / Math.max(categoryOrder.length, 1);
  const categoryWidth = categoryStep * 0.82;
  const barGap = 4;
  const barWidth = Math.max(
    10,
    Math.min(26, (categoryWidth - barGap * Math.max(0, seriesCount - 1)) / seriesCount)
  );
  const groupPixelWidth = barWidth * seriesCount + barGap * Math.max(0, seriesCount - 1);

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const contentGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(contentGroup);

  const yTicks = 5;
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const value = (yMax * tick) / yTicks;
    const y = margin.top + chartHeight - (value / yMax) * chartHeight;
    const grid = document.createElementNS("http://www.w3.org/2000/svg", "line");
    grid.setAttribute("x1", String(margin.left));
    grid.setAttribute("x2", String(width - margin.right));
    grid.setAttribute("y1", String(y));
    grid.setAttribute("y2", String(y));
    grid.setAttribute("stroke", "#64748b66");
    grid.setAttribute("stroke-width", "1");
    contentGroup.appendChild(grid);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 8));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = value.toFixed(2);
    contentGroup.appendChild(label);
  }

  for (const [categoryIndex, category] of categoryOrder.entries()) {
    const centerX = margin.left + categoryStep * categoryIndex + categoryStep / 2;
    const groupStartX = centerX - groupPixelWidth / 2;

    for (const [seriesIndex, series] of seriesOrder.entries()) {
      const point = valueMap.get(`${category}|#|${series}`);
      if (!point) {
        continue;
      }
      const barHeight = (point.mean / yMax) * chartHeight;
      const barY = margin.top + chartHeight - barHeight;
      const barX = groupStartX + seriesIndex * (barWidth + barGap);
      const color = legendModel?.colorBySeries?.get(series) || getBarColor(seriesIndex);

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", String(barX));
      rect.setAttribute("y", String(barY));
      rect.setAttribute("width", String(barWidth));
      rect.setAttribute("height", String(Math.max(0, barHeight)));
      rect.setAttribute("fill", color);
      rect.style.cursor = "crosshair";
      rect.addEventListener("mouseover", (event) => {
        const tooltipLines = [category];
        if (seriesOrder.length > 1) {
          tooltipLines.push(`series: ${point.displaySeries || legendModel?.displayBySeries?.get(series) || series}`);
        }
        tooltipLines.push(
          `mean: ${Number(point.mean).toFixed(4)}`,
          `std:  ${Number(point.std).toFixed(4)}`
        );
        showBarTooltip(event, tooltipLines);
      });
      rect.addEventListener("mousemove", positionBarTooltip);
      rect.addEventListener("mouseout", hideBarTooltip);
      contentGroup.appendChild(rect);

      const errTop = margin.top + chartHeight - ((point.mean + point.std) / yMax) * chartHeight;
      const errBottom = margin.top + chartHeight - ((point.mean - point.std) / yMax) * chartHeight;
      const centerBarX = barX + barWidth / 2;

      const errorLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
      errorLine.setAttribute("x1", String(centerBarX));
      errorLine.setAttribute("x2", String(centerBarX));
      errorLine.setAttribute("y1", String(errTop));
      errorLine.setAttribute("y2", String(errBottom));
      styleErrorBarSegment(errorLine);
      errorLine.setAttribute("stroke-width", "2");
      contentGroup.appendChild(errorLine);

      const capTop = document.createElementNS("http://www.w3.org/2000/svg", "line");
      capTop.setAttribute("x1", String(centerBarX - 5));
      capTop.setAttribute("x2", String(centerBarX + 5));
      capTop.setAttribute("y1", String(errTop));
      capTop.setAttribute("y2", String(errTop));
      styleErrorBarSegment(capTop);
      capTop.setAttribute("stroke-width", "2");
      contentGroup.appendChild(capTop);

      const capBottom = document.createElementNS("http://www.w3.org/2000/svg", "line");
      capBottom.setAttribute("x1", String(centerBarX - 5));
      capBottom.setAttribute("x2", String(centerBarX + 5));
      capBottom.setAttribute("y1", String(errBottom));
      capBottom.setAttribute("y2", String(errBottom));
      styleErrorBarSegment(capBottom);
      capBottom.setAttribute("stroke-width", "2");
      contentGroup.appendChild(capBottom);
    }

    const xLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
    xLabel.setAttribute("x", String(centerX));
    xLabel.setAttribute("y", String(height - margin.bottom + 16));
    xLabel.setAttribute("transform", `rotate(-28 ${centerX} ${height - margin.bottom + 16})`);
    xLabel.setAttribute("text-anchor", "end");
    xLabel.setAttribute("fill", "currentColor");
    xLabel.setAttribute("font-size", "11");
    xLabel.textContent = categoryDisplayMap.get(category) || category;
    contentGroup.appendChild(xLabel);
  }

  scheduleAdaptiveSvgFit(svg, contentGroup, width, height);
  return svg;
}

function collectNumericMetricLeafPaths(value, parts = [], out = new Map()) {
  if (!value || typeof value !== "object") {
    return out;
  }
  for (const [key, child] of Object.entries(value)) {
    const pathParts = [...parts, key];
    if (typeof child === "number" && Number.isFinite(child)) {
      out.set(pathParts.join("|#|"), pathParts);
      continue;
    }
    if (child && typeof child === "object" && !Array.isArray(child)) {
      collectNumericMetricLeafPaths(child, pathParts, out);
    }
  }
  return out;
}

function splitMetricLabelAtLastDot(label) {
  const lastDotIndex = label.lastIndexOf(".");
  if (lastDotIndex === -1) {
    return { prefix: "(root)", suffix: label };
  }
  return {
    prefix: label.slice(0, lastDotIndex),
    suffix: label.slice(lastDotIndex + 1),
  };
}

function getMetricTypeForEvaluationContext(
  activeExperiment,
  evaluationContext = getEvaluationContext(activeExperiment)
) {
  return selectors.getMetricTypeForEvaluationContext(state, activeExperiment, evaluationContext);
}

function getMetricCollectionSourceRunDir(evaluation) {
  return normalizeValue(evaluation?.sourceRunDir ?? evaluation?.runDir).trim();
}

function expandMetricFieldCollectionEvaluation(
  evaluation,
  { collectionType, singularType, fallbackRunDirPrefix }
) {
  if (!evaluation || typeof evaluation !== "object") {
    return [];
  }

  const metricType = normalizeValue(evaluation?.jobReturnValue?.type).trim();
  const sourceRunDir = getMetricCollectionSourceRunDir(evaluation);
  if (metricType === collectionType) {
    const fieldEntries = evaluation.data;
    if (!fieldEntries || typeof fieldEntries !== "object" || Array.isArray(fieldEntries)) {
      return [];
    }

    const baseOverrides =
      evaluation.overrides && typeof evaluation.overrides === "object" && !Array.isArray(evaluation.overrides)
        ? evaluation.overrides
        : {};

    return Object.entries(fieldEntries)
      .filter(([, fieldEntry]) => fieldEntry && typeof fieldEntry === "object" && !Array.isArray(fieldEntry))
      .map(([field, fieldEntry]) => ({
        ...evaluation,
        runDir: sourceRunDir ? `${sourceRunDir}#${field}` : `${fallbackRunDirPrefix}#${field}`,
        sourceRunDir,
        jobReturnValue: {
          ...(evaluation.jobReturnValue || {}),
          type: singularType,
        },
        overrides: {
          ...baseOverrides,
          "metric.field": field,
        },
        data: fieldEntry,
      }));
  }

  return [
    {
      ...evaluation,
      sourceRunDir,
    },
  ];
}

function expandConfusionMatrixLikeEvaluation(evaluation) {
  return expandMetricFieldCollectionEvaluation(evaluation, {
    collectionType: "ConfusionMatrixCollection",
    singularType: "ConfusionMatrix",
    fallbackRunDirPrefix: "confusion-field",
  });
}

function normalizeConfusionMatrixLikeEvaluations(evaluations) {
  return (evaluations || []).flatMap((evaluation) => expandConfusionMatrixLikeEvaluation(evaluation));
}

function expandTpFpFnLikeEvaluation(evaluation) {
  return expandMetricFieldCollectionEvaluation(evaluation, {
    collectionType: "TpFpFnCollectorCollection",
    singularType: "TpFpFnCollector",
    fallbackRunDirPrefix: "tpfpfn-field",
  });
}

function normalizeTpFpFnLikeEvaluations(evaluations) {
  return (evaluations || []).flatMap((evaluation) => expandTpFpFnLikeEvaluation(evaluation));
}

function countDistinctConfusionMatrixRuns(evaluations) {
  return new Set(
    (evaluations || [])
      .map((evaluation) => getMetricCollectionSourceRunDir(evaluation))
      .filter(Boolean)
  ).size;
}

function getConfusionMatrixTitle(experimentEvaluations, evalTabState) {
  const fieldValues = new Set(
    experimentEvaluations
      .map((evaluation) => getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState))
      .filter((value) => value)
  );
  if (fieldValues.size === 0) {
    return "(missing metric.field)";
  }
  if (fieldValues.size === 1) {
    return getPlotDisplayLabel(Array.from(fieldValues)[0]);
  }
  return `mixed metric.field: ${Array.from(fieldValues)
    .sort((a, b) => a.localeCompare(b))
    .map((value) => getPlotDisplayLabel(value))
    .join(", ")}`;
}

// Convert per-evaluation confusion counts into one aligned matrix with mean/std per cell.
// Missing cells are treated as zeros so evaluations with different support can still be aggregated together.
function getConfusionMatrixAggregation(experimentEvaluations) {
  const rowLabels = new Set();
  const colLabels = new Set();
  const evaluationCells = [];

  for (const evaluation of experimentEvaluations) {
    const map = new Map();
    const evalData = evaluation.data || {};
    for (const [actualLabel, predictedMap] of Object.entries(evalData)) {
      if (!predictedMap || typeof predictedMap !== "object" || Array.isArray(predictedMap)) {
        continue;
      }
      for (const [predictedLabel, rawValue] of Object.entries(predictedMap)) {
        if (!Number.isFinite(rawValue)) {
          continue;
        }
        const value = Number(rawValue);
        rowLabels.add(actualLabel);
        colLabels.add(predictedLabel);
        map.set(`${actualLabel}|#|${predictedLabel}`, value);
      }
    }
    evaluationCells.push(map);
  }

  const sortWithForcedLast = (values, forcedLast) =>
    Array.from(values).sort((a, b) => {
      if (a === forcedLast && b !== forcedLast) {
        return 1;
      }
      if (b === forcedLast && a !== forcedLast) {
        return -1;
      }
      return a.localeCompare(b);
    });

  const rows = sortWithForcedLast(rowLabels, "UNASSIGNABLE");
  const cols = sortWithForcedLast(colLabels, "UNDETECTED");
  const cells = new Map();
  for (const row of rows) {
    for (const col of cols) {
      const key = `${row}|#|${col}`;
      const values = evaluationCells.map((cellMap) => cellMap.get(key) ?? 0);
      const stats = meanAndStd(values) || { mean: 0, std: 0 };
      cells.set(key, stats);
    }
  }

  return { rows, cols, cells };
}

function filterConfusionMatrixAggregationByLabelTotal(aggregation, minLabelTotal) {
  const threshold = Number.isFinite(minLabelTotal) ? Math.max(0, Number(minLabelTotal)) : 0;
  if (!aggregation || threshold <= 0) {
    return aggregation;
  }

  const { rows = [], cols = [], cells = new Map() } = aggregation;
  let filteredRows = [...rows];
  let filteredCols = [...cols];
  let rowTotals = new Map();
  let colTotals = new Map();

  while (true) {
    rowTotals = new Map(
      filteredRows.map((row) => [
        row,
        filteredCols.reduce((sum, col) => sum + (cells.get(`${row}|#|${col}`)?.mean ?? 0), 0),
      ])
    );
    colTotals = new Map(
      filteredCols.map((col) => [
        col,
        filteredRows.reduce((sum, row) => sum + (cells.get(`${row}|#|${col}`)?.mean ?? 0), 0),
      ])
    );

    const nextRows = filteredRows.filter((row) => (rowTotals.get(row) ?? 0) >= threshold);
    const nextCols = filteredCols.filter((col) => (colTotals.get(col) ?? 0) >= threshold);
    if (nextRows.length === filteredRows.length && nextCols.length === filteredCols.length) {
      filteredRows = nextRows;
      filteredCols = nextCols;
      break;
    }
    filteredRows = nextRows;
    filteredCols = nextCols;
    if (!filteredRows.length || !filteredCols.length) {
      break;
    }
  }

  rowTotals = new Map(
    filteredRows.map((row) => [
      row,
      filteredCols.reduce((sum, col) => sum + (cells.get(`${row}|#|${col}`)?.mean ?? 0), 0),
    ])
  );
  colTotals = new Map(
    filteredCols.map((col) => [
      col,
      filteredRows.reduce((sum, row) => sum + (cells.get(`${row}|#|${col}`)?.mean ?? 0), 0),
    ])
  );

  const filteredCells = new Map();
  for (const row of filteredRows) {
    for (const col of filteredCols) {
      const key = `${row}|#|${col}`;
      filteredCells.set(key, cells.get(key) || { mean: 0, std: 0 });
    }
  }
  return {
    rows: filteredRows,
    cols: filteredCols,
    cells: filteredCells,
    rowTotals,
    colTotals,
  };
}

function filterTpFpFnAggregationByTotals(aggregation, minLabelTotal, minDocumentTotal) {
  const labelThreshold = Number.isFinite(minLabelTotal) ? Math.max(0, Number(minLabelTotal)) : 0;
  const documentThreshold = Number.isFinite(minDocumentTotal) ? Math.max(0, Number(minDocumentTotal)) : 0;
  if (!aggregation || (labelThreshold <= 0 && documentThreshold <= 0)) {
    return aggregation;
  }

  const { rows = [], cols = [], cells = new Map() } = aggregation;
  let filteredRows = [...rows];
  let filteredCols = [...cols];
  let rowTotals = new Map();
  let colTotals = new Map();

  while (true) {
    rowTotals = new Map(
      filteredRows.map((row) => [
        row,
        filteredCols.reduce((sum, col) => sum + (cells.get(`${row}|#|${col}`)?.presentCount ?? 0), 0),
      ])
    );
    colTotals = new Map(
      filteredCols.map((col) => [
        col,
        filteredRows.reduce((sum, row) => sum + (cells.get(`${row}|#|${col}`)?.presentCount ?? 0), 0),
      ])
    );

    const nextRows = filteredRows.filter((row) => (rowTotals.get(row) ?? 0) >= documentThreshold);
    const nextCols = filteredCols.filter((col) => (colTotals.get(col) ?? 0) >= labelThreshold);
    if (nextRows.length === filteredRows.length && nextCols.length === filteredCols.length) {
      filteredRows = nextRows;
      filteredCols = nextCols;
      break;
    }
    filteredRows = nextRows;
    filteredCols = nextCols;
    if (!filteredRows.length || !filteredCols.length) {
      break;
    }
  }

  rowTotals = new Map(
    filteredRows.map((row) => [
      row,
      filteredCols.reduce((sum, col) => sum + (cells.get(`${row}|#|${col}`)?.presentCount ?? 0), 0),
    ])
  );
  colTotals = new Map(
    filteredCols.map((col) => [
      col,
      filteredRows.reduce((sum, row) => sum + (cells.get(`${row}|#|${col}`)?.presentCount ?? 0), 0),
    ])
  );

  const filteredCells = new Map();
  for (const row of filteredRows) {
    for (const col of filteredCols) {
      const key = `${row}|#|${col}`;
      filteredCells.set(
        key,
        cells.get(key) || {
          rowStates: [],
          counts: { tp: 0, fp: 0, fn: 0, empty: 0 },
          presentCount: 0,
        }
      );
    }
  }

  return {
    ...aggregation,
    rows: filteredRows,
    cols: filteredCols,
    cells: filteredCells,
    rowTotals,
    colTotals,
  };
}


// Render an already-aggregated confusion matrix as an SVG heatmap with values and tooltips.
function createConfusionMatrixHeatmapSvg(aggregation, precision) {
  const { rows, cols, cells } = aggregation;
  const cellSize = 96;
  const margin = { top: 130, right: 20, bottom: 20, left: 280 };
  const width = margin.left + cols.length * cellSize + margin.right;
  const height = margin.top + rows.length * cellSize + margin.bottom;
  const maxMean = Math.max(0, ...Array.from(cells.values()).map((cell) => cell.mean));

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const xAxisTitle = document.createElementNS("http://www.w3.org/2000/svg", "text");
  xAxisTitle.setAttribute("x", String(margin.left + (cols.length * cellSize) / 2));
  xAxisTitle.setAttribute("y", "20");
  xAxisTitle.setAttribute("text-anchor", "middle");
  xAxisTitle.setAttribute("fill", "currentColor");
  xAxisTitle.setAttribute("font-size", "13");
  xAxisTitle.textContent = "Predicted label";
  svg.appendChild(xAxisTitle);

  const yAxisTitle = document.createElementNS("http://www.w3.org/2000/svg", "text");
  yAxisTitle.setAttribute("x", "20");
  yAxisTitle.setAttribute("y", String(margin.top + (rows.length * cellSize) / 2));
  yAxisTitle.setAttribute("transform", `rotate(-90 20 ${margin.top + (rows.length * cellSize) / 2})`);
  yAxisTitle.setAttribute("text-anchor", "middle");
  yAxisTitle.setAttribute("fill", "currentColor");
  yAxisTitle.setAttribute("font-size", "13");
  yAxisTitle.textContent = "Actual label";
  svg.appendChild(yAxisTitle);

  rows.forEach((row, rowIndex) => {
    const y = margin.top + rowIndex * cellSize + cellSize / 2;
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 10));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = getPlotDisplayLabel(row);
    svg.appendChild(label);
  });

  rows.forEach((row, rowIndex) => {
    cols.forEach((col, colIndex) => {
      const key = `${row}|#|${col}`;
      const stats = cells.get(key) || { mean: 0, std: 0 };
      const x = margin.left + colIndex * cellSize;
      const y = margin.top + rowIndex * cellSize;
      const t = maxMean > 0 ? stats.mean / maxMean : 0;
      const fill = interpolateColor([247, 251, 255], [8, 48, 107], t);

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", String(x));
      rect.setAttribute("y", String(y));
      rect.setAttribute("width", String(cellSize));
      rect.setAttribute("height", String(cellSize));
      rect.setAttribute("fill", fill);
      rect.setAttribute("stroke", "#33415555");
      rect.setAttribute("stroke-width", "1");
      rect.style.cursor = "crosshair";
      rect.addEventListener("mouseover", (event) => {
        showBarTooltip(event, [
          `actual:    ${row}`,
          `predicted: ${col}`,
          `mean: ${formatRounded(stats.mean, precision)}`,
          `std:  ${formatRounded(stats.std, precision)}`,
        ]);
      });
      rect.addEventListener("mousemove", positionBarTooltip);
      rect.addEventListener("mouseout", hideBarTooltip);
      svg.appendChild(rect);

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", String(x + cellSize / 2));
      text.setAttribute("y", String(y + cellSize / 2 + 4));
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("fill", t > 0.55 ? "#f8fafc" : "#0f172a");
      text.setAttribute("font-size", "11");
      text.textContent = `${formatRounded(stats.mean, precision)}±${formatRounded(stats.std, precision)}`;
      svg.appendChild(text);
    });
  });

  // Draw predicted-label ticks last so they stay visible above heatmap cells.
  cols.forEach((col, colIndex) => {
    const x = margin.left + colIndex * cellSize + cellSize / 2;
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    const y = margin.top - 10;
    label.setAttribute("x", String(x + 2));
    label.setAttribute("y", String(y));
    label.setAttribute("transform", `rotate(-35 ${x + 2} ${y})`);
    // Anchor from the tick position so the label text grows away from the matrix.
    label.setAttribute("text-anchor", "start");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = getPlotDisplayLabel(col);
    svg.appendChild(label);
  });

  return svg;
}

// Depending on the current tab strategy, group confusion plots either by metric.field or by
// the active prediction/evaluation grouping, while keeping different metric.field values separate.
function buildConfusionTabMap(activeExperiment, plotGroups, experimentEvaluations, labelFields, evalTabState) {
  const tabMap = new Map();
  const normalizedExperimentEvaluations = normalizeConfusionMatrixLikeEvaluations(experimentEvaluations);
  const groupEntries = plotGroups
    .map((group, index) => ({
      key: `group|#|${group.groupId}`,
      label: getGroupLabelForFields(group, labelFields, `group ${index + 1}`, displayPlotGroupFieldName),
      evaluations: normalizeConfusionMatrixLikeEvaluations(
        group.evaluations.filter((evaluation) => getEvaluationExperiment(evaluation) === activeExperiment)
      ),
    }))
    .filter((entry) => entry.evaluations.length > 0);

  if (state.confusionTabsBy === "metric_field") {
    for (const evaluation of normalizedExperimentEvaluations) {
      const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
      const fieldLabel = rawField || "(missing metric.field)";
      if (!tabMap.has(fieldLabel)) {
        tabMap.set(fieldLabel, { label: getPlotDisplayLabel(fieldLabel), plots: [] });
      }
    }

    for (const [fieldKey, tab] of tabMap.entries()) {
      for (const groupEntry of groupEntries) {
        const evaluationsForFieldAndGroup = groupEntry.evaluations.filter((evaluation) => {
          const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
          const fieldLabel = rawField || "(missing metric.field)";
          return fieldLabel === fieldKey;
        });
        if (evaluationsForFieldAndGroup.length === 0) {
          continue;
        }
        tab.plots.push({ label: groupEntry.label, evaluations: evaluationsForFieldAndGroup });
      }
    }
    return tabMap;
  }

  for (const groupEntry of groupEntries) {
    // Split evaluations by metric.field so different fields don't get mixed into one matrix.
    const byField = new Map();
    for (const evaluation of groupEntry.evaluations) {
      const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
      const fieldLabel = rawField || "(missing metric.field)";
      if (!byField.has(fieldLabel)) {
        byField.set(fieldLabel, []);
      }
      byField.get(fieldLabel).push(evaluation);
    }
    const plots = Array.from(byField.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([fieldLabel, evaluations]) => ({
        label: fieldLabel,
        evaluations,
      }));
    tabMap.set(groupEntry.key, { label: groupEntry.label, plots });
  }

  return tabMap;
}

function getTpFpFnOutcomeLabel(outcomeKey) {
  if (outcomeKey === "tp") {
    return "TP";
  }
  if (outcomeKey === "fp") {
    return "FP";
  }
  if (outcomeKey === "fn") {
    return "FN";
  }
  return String(outcomeKey ?? "").toUpperCase();
}

function getTpFpFnPalette(outcomeKey) {
  if (outcomeKey === "tp") {
    return { start: [240, 253, 244], end: [22, 163, 74] };
  }
  if (outcomeKey === "fp") {
    return { start: [255, 247, 237], end: [234, 88, 12] };
  }
  if (outcomeKey === "fn") {
    return { start: [250, 245, 255], end: [126, 34, 206] };
  }
  return { start: [247, 251, 255], end: [8, 48, 107] };
}

function getTpFpFnOutcomeColor(outcomeKey) {
  if (!outcomeKey) {
    return "#e2e8f0";
  }
  return interpolateColor(getTpFpFnPalette(outcomeKey).start, getTpFpFnPalette(outcomeKey).end, 1);
}

function normalizeTpFpFnCollectorData(rawData) {
  const result = {};

  const getRecordEntry = (recordId) => {
    const key = normalizeValue(recordId) || "(missing record_id)";
    if (!result[key]) {
      result[key] = { tp: [], fp: [], fn: [] };
    }
    return result[key];
  };

  const appendUniqueValues = (target, bucket, values) => {
    if (!Array.isArray(values)) {
      return;
    }
    const seen = new Set(target[bucket]);
    for (const value of values) {
      const normalized = normalizeValue(value);
      if (seen.has(normalized)) {
        continue;
      }
      seen.add(normalized);
      target[bucket].push(normalized);
    }
    target[bucket].sort((a, b) => sortCollator.compare(a, b));
  };

  if (!rawData || typeof rawData !== "object" || Array.isArray(rawData)) {
    return result;
  }

  const looksLikeGlobalOutput = TP_FP_FN_KEYS.some((bucket) => Array.isArray(rawData?.[bucket]));
  if (looksLikeGlobalOutput) {
    for (const bucket of TP_FP_FN_KEYS) {
      const entries = Array.isArray(rawData[bucket]) ? rawData[bucket] : [];
      for (const entry of entries) {
        if (!Array.isArray(entry) || entry.length < 2) {
          continue;
        }
        appendUniqueValues(getRecordEntry(entry[0]), bucket, [entry[1]]);
      }
    }
    return result;
  }

  for (const [recordId, entry] of Object.entries(rawData)) {
    const normalizedEntry = entry && typeof entry === "object" && !Array.isArray(entry) ? entry : {};
    const target = getRecordEntry(recordId);
    for (const bucket of TP_FP_FN_KEYS) {
      appendUniqueValues(target, bucket, normalizedEntry[bucket]);
    }
  }

  return result;
}

function getTpFpFnCombinedAggregation(experimentEvaluations) {
  const rowLabels = new Set();
  const colLabels = new Set();
  const evaluationCells = [];
  const evaluationLabels = [];

  for (const [evaluationIndex, evaluation] of experimentEvaluations.entries()) {
    const map = new Map();
    evaluationLabels.push(normalizeValue(evaluation?.runDir) || `evaluation ${evaluationIndex + 1}`);
    const normalizedData = normalizeTpFpFnCollectorData(evaluation.data);
    for (const [recordId, recordEntry] of Object.entries(normalizedData)) {
      rowLabels.add(recordId);
      const entriesByLabel = new Map();
      for (const outcomeKey of TP_FP_FN_KEYS) {
        const labels = Array.isArray(recordEntry?.[outcomeKey]) ? recordEntry[outcomeKey] : [];
        for (const label of labels) {
          colLabels.add(label);
          if (!entriesByLabel.has(label)) {
            entriesByLabel.set(label, { tp: false, fp: false, fn: false });
          }
          entriesByLabel.get(label)[outcomeKey] = true;
        }
      }
      for (const [label, rowState] of entriesByLabel.entries()) {
        map.set(`${recordId}|#|${label}`, rowState);
      }
    }
    evaluationCells.push(map);
  }

  const rows = Array.from(rowLabels).sort((a, b) => sortCollator.compare(a, b));
  const cols = Array.from(colLabels).sort((a, b) => sortCollator.compare(a, b));
  const cells = new Map();

  for (const row of rows) {
    for (const col of cols) {
      const key = `${row}|#|${col}`;
      const rowStates = evaluationCells.map(
        (cellMap) => cellMap.get(key) || { tp: false, fp: false, fn: false }
      );
      const counts = { tp: 0, fp: 0, fn: 0, empty: 0 };
      for (const rowState of rowStates) {
        let rowHasAny = false;
        for (const outcomeKey of TP_FP_FN_KEYS) {
          if (rowState[outcomeKey]) {
            counts[outcomeKey] += 1;
            rowHasAny = true;
          }
        }
        if (!rowHasAny) {
          counts.empty += 1;
        }
      }
      cells.set(key, {
        rowStates,
        counts,
        presentCount: counts.tp + counts.fp + counts.fn,
      });
    }
  }

  return {
    rows,
    cols,
    cells,
    totalEvaluations: evaluationCells.length,
    evaluationLabels,
  };
}

function buildTpFpFnTabMap(plotGroups, experimentEvaluations, labelFields, evalTabState) {
  const tabMap = new Map();
  const normalizedExperimentEvaluations = normalizeTpFpFnLikeEvaluations(experimentEvaluations);

  const groupEntries = plotGroups
    .map((group, index) => ({
      key: `group|#|${group.groupId}`,
      label: getGroupLabelForFields(group, labelFields, `group ${index + 1}`, displayPlotGroupFieldName),
      evaluations: normalizeTpFpFnLikeEvaluations(group.evaluations),
    }))
    .filter((entry) => entry.evaluations.length > 0);

  if (state.confusionTabsBy === "metric_field") {
    for (const evaluation of normalizedExperimentEvaluations) {
      const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
      const fieldLabel = rawField || "(missing metric.field)";
      if (!tabMap.has(fieldLabel)) {
        tabMap.set(fieldLabel, { label: getPlotDisplayLabel(fieldLabel), plots: [] });
      }
    }

    for (const [fieldKey, tab] of tabMap.entries()) {
      for (const groupEntry of groupEntries) {
        const evaluationsForFieldAndGroup = groupEntry.evaluations.filter((evaluation) => {
          const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
          const fieldLabel = rawField || "(missing metric.field)";
          return fieldLabel === fieldKey;
        });
        if (evaluationsForFieldAndGroup.length === 0) {
          continue;
        }
        tab.plots.push({ label: groupEntry.label, fieldLabel: fieldKey, evaluations: evaluationsForFieldAndGroup });
      }
    }
    return tabMap;
  }

  for (const groupEntry of groupEntries) {
    const byField = new Map();
    for (const evaluation of groupEntry.evaluations) {
      const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
      const fieldLabel = rawField || "(missing metric.field)";
      if (!byField.has(fieldLabel)) {
        byField.set(fieldLabel, []);
      }
      byField.get(fieldLabel).push(evaluation);
    }
    const plots = Array.from(byField.entries())
      .sort(([a], [b]) => sortCollator.compare(a, b))
      .map(([fieldLabel, evaluations]) => ({
        label: fieldLabel,
        fieldLabel,
        evaluations,
      }));
    tabMap.set(groupEntry.key, { label: groupEntry.label, plots });
  }

  return tabMap;
}

function createTpFpFnLegendElement() {
  return createPlotLegendElement([
    { label: "TP", color: getTpFpFnOutcomeColor("tp") },
    { label: "FP", color: getTpFpFnOutcomeColor("fp") },
    { label: "FN", color: getTpFpFnOutcomeColor("fn") },
  ]);
}

function buildTpFpFnCellSummary(row, col, stats, totalEvaluations, evaluationLabels, precision) {
  const tpShare = totalEvaluations ? (stats.counts.tp / totalEvaluations) * 100 : 0;
  const fpShare = totalEvaluations ? (stats.counts.fp / totalEvaluations) * 100 : 0;
  const fnShare = totalEvaluations ? (stats.counts.fn / totalEvaluations) * 100 : 0;
  const evaluations = stats.rowStates.map((rowState, evalIndex) => {
    const outcomes = TP_FP_FN_KEYS.filter((bucket) => rowState[bucket]);
    return {
      run_dir: evaluationLabels[evalIndex] || `evaluation ${evalIndex + 1}`,
      value: outcomes.map((bucket) => getTpFpFnOutcomeLabel(bucket)).join(", ") || "empty",
    };
  });

  const lines = [
    `document: ${row}`,
    `label:    ${col}`,
    `TP/FP/FN %: ${formatRounded(tpShare, precision)} / ${formatRounded(fpShare, precision)} / ${formatRounded(fnShare, precision)}`,
  ];

  return {
    lines,
    payload: {
      document_id: row,
      label: col,
      counts: {
        tp: stats.counts.tp,
        fp: stats.counts.fp,
        fn: stats.counts.fn,
        empty: stats.counts.empty,
      },
      percentages: {
        tp: tpShare,
        fp: fpShare,
        fn: fnShare,
      },
      evaluations,
    },
  };
}

function createTpFpFnCombinedMatrixSvg(aggregation, precision) {
  const { rows, cols, cells, totalEvaluations, evaluationLabels } = aggregation;
  const miniCellWidth = 18;
  const miniCellHeight = 18;
  const miniGap = 2;
  const cellPadding = 4;
  const outcomeCols = TP_FP_FN_KEYS.length;
  const cellWidth = Math.max(
    52,
    outcomeCols * miniCellWidth + Math.max(0, outcomeCols - 1) * miniGap + cellPadding * 2
  );
  const cellHeight = Math.max(28, miniCellHeight + cellPadding * 2);
  const margin = { top: 140, right: 20, bottom: 20, left: 120 };
  const width = margin.left + cols.length * cellWidth + margin.right;
  const height = margin.top + rows.length * cellHeight + margin.bottom;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const contentGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(contentGroup);

  const xAxisTitle = document.createElementNS("http://www.w3.org/2000/svg", "text");
  xAxisTitle.setAttribute("x", String(margin.left + (cols.length * cellWidth) / 2));
  xAxisTitle.setAttribute("y", "20");
  xAxisTitle.setAttribute("text-anchor", "middle");
  xAxisTitle.setAttribute("fill", "currentColor");
  xAxisTitle.setAttribute("font-size", "13");
  xAxisTitle.textContent = "Label";
  contentGroup.appendChild(xAxisTitle);

  const yAxisTitle = document.createElementNS("http://www.w3.org/2000/svg", "text");
  yAxisTitle.setAttribute("x", "18");
  yAxisTitle.setAttribute("y", String(margin.top + (rows.length * cellHeight) / 2));
  yAxisTitle.setAttribute("transform", `rotate(-90 18 ${margin.top + (rows.length * cellHeight) / 2})`);
  yAxisTitle.setAttribute("text-anchor", "middle");
  yAxisTitle.setAttribute("fill", "currentColor");
  yAxisTitle.setAttribute("font-size", "13");
  yAxisTitle.textContent = "Document id";
  contentGroup.appendChild(yAxisTitle);

  rows.forEach((row, rowIndex) => {
    const y = margin.top + rowIndex * cellHeight + cellHeight / 2;
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 10));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = row;
    contentGroup.appendChild(label);
  });

  cols.forEach((col, colIndex) => {
    const labelStartX = margin.left + colIndex * cellWidth;
    const x = labelStartX + cellWidth / 2;
    const y = margin.top - 12;
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(x + 2));
    label.setAttribute("y", String(y));
    label.setAttribute("transform", `rotate(-35 ${x + 2} ${y})`);
    label.setAttribute("text-anchor", "start");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = getPlotDisplayLabel(col);
    contentGroup.appendChild(label);
  });

  rows.forEach((row, rowIndex) => {
    cols.forEach((col, colIndex) => {
      const key = `${row}|#|${col}`;
      const stats = cells.get(key) || {
        rowStates: Array.from({ length: totalEvaluations }, () => ({ tp: false, fp: false, fn: false })),
        counts: { tp: 0, fp: 0, fn: 0, empty: totalEvaluations },
        presentCount: 0,
      };
      const x = margin.left + colIndex * cellWidth;
      const y = margin.top + rowIndex * cellHeight;

      const cellBorder = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      cellBorder.setAttribute("x", String(x));
      cellBorder.setAttribute("y", String(y));
      cellBorder.setAttribute("width", String(cellWidth));
      cellBorder.setAttribute("height", String(cellHeight));
      cellBorder.setAttribute("fill", "#ffffff");
      cellBorder.setAttribute("stroke", "#33415555");
      cellBorder.setAttribute("stroke-width", "1");
      contentGroup.appendChild(cellBorder);

      TP_FP_FN_KEYS.forEach((outcomeKey, outcomeIndex) => {
        const subX = x + cellPadding + outcomeIndex * (miniCellWidth + miniGap);
        const subY = y + cellPadding;
        const share = totalEvaluations ? stats.counts[outcomeKey] / totalEvaluations : 0;
        const palette = getTpFpFnPalette(outcomeKey);
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", String(subX));
        rect.setAttribute("y", String(subY));
        rect.setAttribute("width", String(miniCellWidth));
        rect.setAttribute("height", String(miniCellHeight));
        rect.setAttribute("rx", "2");
        rect.setAttribute("fill", interpolateColor(palette.start, palette.end, share));
        rect.setAttribute("stroke", "#ffffffcc");
        rect.setAttribute("stroke-width", "1");
        contentGroup.appendChild(rect);
      });

      const overlay = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      overlay.setAttribute("x", String(x));
      overlay.setAttribute("y", String(y));
      overlay.setAttribute("width", String(cellWidth));
      overlay.setAttribute("height", String(cellHeight));
      overlay.setAttribute("fill", "transparent");
      overlay.style.cursor = "pointer";
      overlay.addEventListener("mouseover", (event) => {
        const summary = buildTpFpFnCellSummary(
          row,
          col,
          stats,
          totalEvaluations,
          evaluationLabels,
          precision
        );
        showBarTooltip(event, summary.lines);
      });
      overlay.addEventListener("mousemove", positionBarTooltip);
      overlay.addEventListener("mouseout", hideBarTooltip);
      overlay.addEventListener("click", async (event) => {
        const summary = buildTpFpFnCellSummary(
          row,
          col,
          stats,
          totalEvaluations,
          evaluationLabels,
          precision
        );
        try {
          await writeTextToClipboard(JSON.stringify(summary.payload, null, 2));
          showBarTooltip(event, [...summary.lines, "", "Copied JSON to clipboard."]);
        } catch (error) {
          console.warn("Failed to copy TpFpFn cell summary to clipboard.", error);
          showBarTooltip(event, [...summary.lines, "", "Copy to clipboard failed."]);
        }
      });
      contentGroup.appendChild(overlay);
    });
  });

  scheduleAdaptiveSvgFit(svg, contentGroup, width, height);
  return svg;
}

function buildPlotEntries(metricPaths, plotGroups, groupBarFields, categoryFields) {
  const entries = [];
  for (const metricPath of metricPaths) {
    const points = [];
    plotGroups.forEach((group, index) => {
      const values = group.evaluations
            .map((evaluation) => Number(getValueAtPath(evaluation.data, metricPath.parts)))
        .filter((value) => Number.isFinite(value));
      const stats = meanAndStd(values);
      if (!stats) {
        return;
      }
      const categoryLabel = groupBarFields.length
        ? getGroupLabelForFields(group, categoryFields, "all")
        : getGroupLabelForFields(group, categoryFields, `group ${index + 1}`);
      const displayCategoryLabel = groupBarFields.length
        ? getGroupLabelForFields(group, categoryFields, "all", displayPlotGroupFieldName)
        : getGroupLabelForFields(group, categoryFields, `group ${index + 1}`, displayPlotGroupFieldName);
      const seriesLabel = groupBarFields.length
        ? getGroupLabelForFields(group, groupBarFields, "series")
        : "__single__";
      const displaySeriesLabel = groupBarFields.length
        ? getGroupLabelForFields(group, groupBarFields, "series", displayPlotGroupFieldName)
        : "__single__";
      points.push({
        label: categoryLabel,
        displayLabel: displayCategoryLabel,
        category: categoryLabel,
        displayCategory: displayCategoryLabel,
        series: seriesLabel,
        displaySeries: displaySeriesLabel,
        mean: stats.mean,
        std: stats.std,
      });
    });
    if (!points.length) {
      continue;
    }
    const split = splitMetricLabelAtLastDot(metricPath.label);
    entries.push({ metricLabel: metricPath.label, parts: metricPath.parts, points, ...split });
  }
  return entries;
}

function buildBarsTabMap(plotEntries) {
  const tabMap = new Map();
  for (const entry of plotEntries) {
    const tabKey = state.plotTabsBy === "suffix" ? entry.suffix : entry.prefix;
    if (!tabMap.has(tabKey)) {
      tabMap.set(tabKey, []);
    }
    tabMap.get(tabKey).push(entry);
  }
  return tabMap;
}

function buildErrorsTabMap(plotEntries) {
  const totalKeys = new Set(["with_error", "no_error"]);
  const total = plotEntries.filter((entry) => totalKeys.has(entry.parts[0]));
  const details = plotEntries.filter((entry) => !totalKeys.has(entry.parts[0]));
  const tabMap = new Map();
  if (total.length) {
    tabMap.set("total", total);
  }
  if (details.length) {
    tabMap.set("details", details);
  }
  return tabMap;
}

function renderPlotTabsAndGrid(tabMap, activeExperiment, groupBarFields, metricType) {
  const tabPriority = ["total", "details"];
  const sortedTabKeys = Array.from(tabMap.keys()).sort((a, b) => {
    const pa = tabPriority.indexOf(a);
    const pb = tabPriority.indexOf(b);
    if (pa !== -1 && pb !== -1) return pa - pb;
    if (pa !== -1) return -1;
    if (pb !== -1) return 1;
    return a.localeCompare(b);
  });
  state.activeEvalPlotTab = resolveActiveTabValue(state.activeEvalPlotTab, sortedTabKeys);
  renderTabButtons({
    documentLike: document,
    containerElement: evalPlotTabs,
    tabModels: buildCountTabButtonModels(sortedTabKeys, {
      activeValue: state.activeEvalPlotTab,
      getLabelText: (key) => key,
      getCount: (key) => tabMap.get(key).length,
      getTitle: (key) => key,
    }),
    onSelect: (key) => {
      if (state.activeEvalPlotTab === key) {
        return;
      }
      state.activeEvalPlotTab = key;
      renderEvaluationPlots(activeExperiment);
    },
  });
  const activeEntries = tabMap.get(state.activeEvalPlotTab) || [];
  const groupedLegendModel = groupBarFields.length
    ? buildGroupedLegendModel(activeEntries)
    : null;
  const hasSharedLegend = Boolean(groupedLegendModel && groupedLegendModel.items.length > 1);
  state.activePlotLegendItems = hasSharedLegend ? groupedLegendModel.items : [];
  plotShowLegendOnceRow.style.display = hasSharedLegend ? "" : "none";

  if (hasSharedLegend && state.plotShowLegendOnce) {
    evalPlotContent.appendChild(createPlotLegendElement(groupedLegendModel.items));
  }

  const grid = document.createElement("div");
  grid.className = "plot-grid";
  for (const entry of activeEntries) {
    const card = document.createElement("section");
    card.className = "plot-card";
    const title = document.createElement("p");
    title.className = "plot-title";
    const groupedByText = groupBarFields.length
      ? ` | grouped by: ${groupBarFields.map((f) => displayPlotGroupFieldName(f)).join(", ")}`
      : "";
    title.textContent = `${getPlotTitleLabel(entry, metricType)} (mean ± std)${groupedByText}`;
    card.appendChild(title);
    if (groupBarFields.length) {
      const plotLegendItems = getLegendItemsForPoints(entry.points, groupedLegendModel);
      if (plotLegendItems.length > 1 && !state.plotShowLegendOnce) {
        card.appendChild(createPlotLegendElement(plotLegendItems));
      }
      card.appendChild(createGroupedBarPlotSvg(entry.points, groupedLegendModel));
    } else {
      card.appendChild(createBarPlotSvg(entry.points));
    }
    grid.appendChild(card);
  }
  if (!grid.childElementCount) {
    const msg = document.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = "No plottable metric values found for the active tab.";
    evalPlotContent.appendChild(msg);
    return;
  }
  evalPlotContent.appendChild(grid);
}

// Plot rendering always starts from the currently selected prediction groups and selected eval groups,
// then branches into metric-specific aggregation/rendering.
/**
 * Render evaluation plots from the current selector-derived evaluation context.
 */
function renderEvaluationPlots(
  activeExperiment,
  evaluationContext = getEvaluationContext(activeExperiment)
) {
  renderPlotControls({
    metricType: null,
    plotTabsBy: state.plotTabsBy,
    confusionTabsBy: state.confusionTabsBy,
    plotShortenLabels: state.plotShortenLabels,
    plotRoundingPrecision: state.plotRoundingPrecision,
    plotConfusionMinLabelTotal: state.plotConfusionMinLabelTotal,
    plotTpFpFnMinLabelTotal: state.plotTpFpFnMinLabelTotal,
    plotTpFpFnMinDocumentTotal: state.plotTpFpFnMinDocumentTotal,
    plotShowLegendOnce: state.plotShowLegendOnce,
    exportOpaqueBackground: state.exportOpaqueBackground,
    plotTabsByPrefixButton,
    plotTabsBySuffixButton,
    confusionTabsByMetricFieldButton,
    confusionTabsByPredictionGroupButton,
    plotShortenLabelsInput: plotShortenLabels,
    plotRoundingPrecisionInput: plotRoundingPrecision,
    plotConfusionMinLabelTotalRow,
    plotConfusionMinLabelTotalInput: plotConfusionMinLabelTotal,
    plotTpFpFnMinLabelTotalRow,
    plotTpFpFnMinLabelTotalInput: plotTpFpFnMinLabelTotal,
    plotTpFpFnMinDocumentTotalRow,
    plotTpFpFnMinDocumentTotalInput: plotTpFpFnMinDocumentTotal,
    plotTabsByRow,
    plotConfusionTabsByRow,
    plotGroupBarsRow,
    plotShowLegendOnceRow,
    plotShowLegendOnceInput: plotShowLegendOnce,
    exportOpaqueBackgroundInput: exportOpaqueBackground,
  });
  evalPlotTabs.innerHTML = "";
  evalPlotContent.innerHTML = "";
  plotGroupBarsList.innerHTML = "";
  state.activePlotLegendItems = [];

  const selectedPredictionGroups = getSelectedPredictionGroups();
  if (selectedPredictionGroups.length === 0) {
    const msg = document.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = "Select prediction groups to generate plots.";
    evalPlotContent.appendChild(msg);
    return;
  }

  if (!evaluationContext) {
    const msg = document.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = "Select one or more prediction groups to generate plots.";
    evalPlotContent.appendChild(msg);
    return;
  }

  const { experimentEvaluations, evalTabState } = evaluationContext;
  const metricType = getMetricTypeForEvaluationContext(activeExperiment, evaluationContext);
  renderPlotControls({
    metricType,
    plotTabsBy: state.plotTabsBy,
    confusionTabsBy: state.confusionTabsBy,
    plotShortenLabels: state.plotShortenLabels,
    plotRoundingPrecision: state.plotRoundingPrecision,
    plotConfusionMinLabelTotal: state.plotConfusionMinLabelTotal,
    plotTpFpFnMinLabelTotal: state.plotTpFpFnMinLabelTotal,
    plotTpFpFnMinDocumentTotal: state.plotTpFpFnMinDocumentTotal,
    plotShowLegendOnce: state.plotShowLegendOnce,
    exportOpaqueBackground: state.exportOpaqueBackground,
    plotTabsByPrefixButton,
    plotTabsBySuffixButton,
    confusionTabsByMetricFieldButton,
    confusionTabsByPredictionGroupButton,
    plotShortenLabelsInput: plotShortenLabels,
    plotRoundingPrecisionInput: plotRoundingPrecision,
    plotConfusionMinLabelTotalRow,
    plotConfusionMinLabelTotalInput: plotConfusionMinLabelTotal,
    plotTpFpFnMinLabelTotalRow,
    plotTpFpFnMinLabelTotalInput: plotTpFpFnMinLabelTotal,
    plotTpFpFnMinDocumentTotalRow,
    plotTpFpFnMinDocumentTotalInput: plotTpFpFnMinDocumentTotal,
    plotTabsByRow,
    plotConfusionTabsByRow,
    plotGroupBarsRow,
    plotShowLegendOnceRow,
    plotShowLegendOnceInput: plotShowLegendOnce,
    exportOpaqueBackgroundInput: exportOpaqueBackground,
  });
  const selectedEvalGroups = getSelectedEvaluationGroups(evaluationContext);
  if (selectedEvalGroups.length === 0) {
    const msg = document.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = "Select evaluation groups to generate plots.";
    evalPlotContent.appendChild(msg);
    return;
  }

  if (
    metricType !== "ConfusionMatrix" &&
    metricType !== "ErrorCollector" &&
    metricType !== "F1MicroMultipleFieldsMetric" &&
    metricType !== "TpFpFnCollector"
  ) {
    const msg = document.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = `(unknown metric type: ${metricType || "(missing)"}, data visualization not yet implemented)`;
    evalPlotContent.appendChild(msg);
    return;
  }

  const combined = getPlotGroups(
    activeExperiment,
    selectedEvalGroups,
    evalTabState.groupByFields,
    evalTabState
  );
  const plotGroups = combined.groups;
  const plotGroupFields = combined.fields;
  const varyingPlotGroupFields = getVaryingFields(plotGroups, plotGroupFields);

  if (metricType === "ConfusionMatrix") {
    // Confusion plots do not reuse the generic metric plot path below; they get their own tab map
    // and heatmap rendering because the aggregation shape is matrix-like instead of metric-like.
    const labelFields = varyingPlotGroupFields.length ? varyingPlotGroupFields : plotGroupFields;
    const confusionTabMap = buildConfusionTabMap(
      activeExperiment,
      plotGroups,
      experimentEvaluations,
      labelFields,
      evalTabState
    );
    const sortedConfusionTabKeys = Array.from(confusionTabMap.keys()).sort((a, b) =>
      confusionTabMap.get(a).label.localeCompare(confusionTabMap.get(b).label)
    );
    if (sortedConfusionTabKeys.length === 0) {
      const msg = document.createElement("p");
      msg.className = "plot-empty";
      msg.textContent = `No confusion matrix data found for ${activeExperiment}.`;
      evalPlotContent.appendChild(msg);
      return;
    }

    state.activeEvalPlotTab = resolveActiveTabValue(state.activeEvalPlotTab, sortedConfusionTabKeys);
    renderTabButtons({
      documentLike: document,
      containerElement: evalPlotTabs,
      tabModels: buildCountTabButtonModels(sortedConfusionTabKeys, {
        activeValue: state.activeEvalPlotTab,
        getLabelText: (key) => confusionTabMap.get(key).label,
        getCount: (key) => {
          const entry = confusionTabMap.get(key);
          return countDistinctConfusionMatrixRuns(
            entry.plots.flatMap((plot) => plot.evaluations)
          );
        },
        getTitle: (key) => confusionTabMap.get(key).label,
      }),
      onSelect: (key) => {
        if (state.activeEvalPlotTab === key) {
          return;
        }
        state.activeEvalPlotTab = key;
        renderEvaluationPlots(activeExperiment);
      },
    });

    const activeConfusionEntry = confusionTabMap.get(state.activeEvalPlotTab);
    const grid = document.createElement("div");
    grid.className = "plot-grid";

    for (const plotEntry of activeConfusionEntry.plots) {
      const aggregation = filterConfusionMatrixAggregationByLabelTotal(
        getConfusionMatrixAggregation(plotEntry.evaluations),
        state.plotConfusionMinLabelTotal
      );
      if (!aggregation.rows.length || !aggregation.cols.length) {
        continue;
      }

      const card = document.createElement("section");
      card.className = "plot-card";
      const title = document.createElement("p");
      title.className = "plot-title";
      const fieldTitle = getConfusionMatrixTitle(plotEntry.evaluations, evalTabState);
      if (state.confusionTabsBy === "metric_field") {
        title.textContent = `${plotEntry.label} (mean ± std)`;
      } else {
        title.textContent = `${fieldTitle} (mean ± std)`;
      }
      card.appendChild(title);
      card.appendChild(
        createConfusionMatrixHeatmapSvg(aggregation, state.plotRoundingPrecision)
      );
      grid.appendChild(card);
    }

    if (!grid.childElementCount) {
      const msg = document.createElement("p");
      msg.className = "plot-empty";
      msg.textContent = `No confusion matrix values found for ${activeConfusionEntry.label} with minimum label total ${state.plotConfusionMinLabelTotal}.`;
      evalPlotContent.appendChild(msg);
      return;
    }

    evalPlotContent.appendChild(grid);
    return;
  }

  if (metricType === "TpFpFnCollector") {
    const labelFields = varyingPlotGroupFields.length ? varyingPlotGroupFields : plotGroupFields;
    const tpfpfnTabMap = buildTpFpFnTabMap(
      plotGroups,
      experimentEvaluations,
      labelFields,
      evalTabState
    );
    const sortedTabKeys = Array.from(tpfpfnTabMap.keys()).sort((a, b) =>
      tpfpfnTabMap.get(a).label.localeCompare(tpfpfnTabMap.get(b).label)
    );
    if (!sortedTabKeys.length) {
      const msg = document.createElement("p");
      msg.className = "plot-empty";
      msg.textContent = `No ${metricType} data found for ${activeExperiment}.`;
      evalPlotContent.appendChild(msg);
      return;
    }

    state.activeEvalPlotTab = resolveActiveTabValue(state.activeEvalPlotTab, sortedTabKeys);
    renderTabButtons({
      documentLike: document,
      containerElement: evalPlotTabs,
      tabModels: buildCountTabButtonModels(sortedTabKeys, {
        activeValue: state.activeEvalPlotTab,
        getLabelText: (key) => tpfpfnTabMap.get(key).label,
        getCount: (key) => {
          const entry = tpfpfnTabMap.get(key);
          return entry.plots.reduce(
            (sum, plot) => sum + plot.evaluations.length,
            0
          );
        },
        getTitle: (key) => {
          const entry = tpfpfnTabMap.get(key);
          const evaluationCount = entry.plots.reduce(
            (sum, plot) => sum + plot.evaluations.length,
            0
          );
          return `${entry.label} (${evaluationCount} grouped evaluations)`;
        },
      }),
      onSelect: (key) => {
        if (state.activeEvalPlotTab === key) {
          return;
        }
        state.activeEvalPlotTab = key;
        renderEvaluationPlots(activeExperiment);
      },
    });

    const activeEntry = tpfpfnTabMap.get(state.activeEvalPlotTab);
    const grid = document.createElement("div");
    grid.className = "plot-grid";

    for (const plotEntry of activeEntry.plots) {
      const aggregation = filterTpFpFnAggregationByTotals(
        getTpFpFnCombinedAggregation(plotEntry.evaluations),
        state.plotTpFpFnMinLabelTotal,
        state.plotTpFpFnMinDocumentTotal
      );
      if (!aggregation.rows.length || !aggregation.cols.length) {
        continue;
      }

      const card = document.createElement("section");
      card.className = "plot-card";
      const title = document.createElement("p");
      title.className = "plot-title";
      const fieldTitle = getConfusionMatrixTitle(plotEntry.evaluations, evalTabState);
      if (state.confusionTabsBy === "metric_field") {
        title.textContent = `${plotEntry.label} (${aggregation.totalEvaluations} grouped evals)`;
      } else {
        title.textContent = `${fieldTitle} (${aggregation.totalEvaluations} grouped evals)`;
      }
      card.appendChild(title);
      card.appendChild(createTpFpFnCombinedMatrixSvg(aggregation, state.plotRoundingPrecision));
      grid.appendChild(card);
    }

    if (!grid.childElementCount) {
      const msg = document.createElement("p");
      msg.className = "plot-empty";
      msg.textContent = `No TP/FP/FN values found for ${activeEntry.label} with minimum label total ${state.plotTpFpFnMinLabelTotal} and minimum document total ${state.plotTpFpFnMinDocumentTotal}.`;
      evalPlotContent.appendChild(msg);
      return;
    }

    evalPlotContent.appendChild(createTpFpFnLegendElement());
    evalPlotContent.appendChild(grid);
    return;
  }

  const metricPaths = Array.from(
    experimentEvaluations.reduce(
      (acc, evaluation) => collectNumericMetricLeafPaths(evaluation.data, [], acc),
      new Map()
    )
  )
    .map(([, pathParts]) => ({ parts: pathParts, label: pathParts.join(".") }))
    .sort((a, b) => a.label.localeCompare(b.label));

  if (metricPaths.length === 0) {
    const msg = document.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = `No numeric metric data found for ${activeExperiment}.`;
    evalPlotContent.appendChild(msg);
    return;
  }

  const varyingGroupByFields = varyingPlotGroupFields;
  state.plotGroupBarFields = new Set(
    Array.from(state.plotGroupBarFields).filter((field) => new Set(varyingGroupByFields).has(field))
  );
  renderPlotGroupBarChips({
    documentLike: document,
    listElement: plotGroupBarsList,
    availableFields: varyingGroupByFields,
    checkedValues: state.plotGroupBarFields,
    getLabel: displayPlotGroupFieldName,
    onToggle: (field, checked) => {
      if (checked) {
        state.plotGroupBarFields.add(field);
      } else {
        state.plotGroupBarFields.delete(field);
      }
      renderEvaluationPlots(activeExperiment);
    },
  });

  const groupBarFields = varyingGroupByFields.filter((field) => state.plotGroupBarFields.has(field));
  const categoryFields = varyingGroupByFields.filter((field) => !groupBarFields.includes(field));

  const plotEntries = buildPlotEntries(metricPaths, plotGroups, groupBarFields, categoryFields);
  if (!plotEntries.length) {
    const msg = document.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = `No plottable metric values found for ${activeExperiment}.`;
    evalPlotContent.appendChild(msg);
    return;
  }

  const tabMap = metricType === "ErrorCollector"
    ? buildErrorsTabMap(plotEntries)
    : buildBarsTabMap(plotEntries);

  renderPlotTabsAndGrid(tabMap, activeExperiment, groupBarFields, metricType);
}

/**
 * Render the evaluation table, JSON pane, and plots from selector-derived evaluation state.
 */
function renderEvaluations() {
  evalTabs.innerHTML = "";
  evaluationsTable.innerHTML = "";
  renderEvalJsonPane({
    layoutElement: evalLayout,
    titleElement: evalJsonTitle,
    codeElement: evalJsonCode,
    evaluationButton: evalJsonTabEvaluation,
    predictionButton: evalJsonTabPrediction,
    activeTab: state.activeEvalJsonTab,
  });
  renderGroupByButtonState(
    {
      allButton: evalGroupByAllButton,
      toggleButton: evalGroupByToggleButton,
      noneButton: evalGroupByNoneButton,
    },
    []
  );
  renderSortStatus({
    labelElement: evalSortedByLabel,
    resetButton: evalResetSortButton,
    sortConfig: [],
    validColumns: [],
    displayColumnName: displayEvalColumnName,
  });
  evalDefaultsList.innerHTML = "";

  const selectedEvaluations = gatherSelectedEvaluations();
  if (!selectedEvaluations.length) {
    setPanelVisibility(evalDefaultsPanel, false);
    evalSummary.textContent = "Select one or more prediction groups to view evaluation overrides and job_return_value fields.";
    renderEvaluationPlots(state.activeEvalTab || "");
    return;
  }

  const byExperiment = getEvaluationsByExperiment(selectedEvaluations);

  const experiments = Array.from(byExperiment.keys()).sort();
  state.activeEvalTab = resolveActiveTabValue(state.activeEvalTab, experiments);
  renderTabButtons({
    documentLike: document,
    containerElement: evalTabs,
    tabModels: buildCountTabButtonModels(experiments, {
      activeValue: state.activeEvalTab,
      getLabelText: (experiment) => experiment,
      getCount: (experiment) => byExperiment.get(experiment).length,
    }),
    onSelect: (experiment) => {
      if (state.activeEvalTab === experiment) {
        return;
      }
      state.activeEvalTab = experiment;
      renderEvaluations();
    },
  });

  const evaluationContext = getEvaluationContext(state.activeEvalTab, selectedEvaluations);
  const {
    experimentEvaluations,
    evalColumns,
    evalTabState,
    evaluationGroups,
  } = evaluationContext;
  const evalColumnSections = getEvalColumnSections(evalColumns);
  const orderedEvalColumns = evalColumnSections.flatMap((section) => section.columns);
  evalTabState.sort = renderSortStatus({
    labelElement: evalSortedByLabel,
    resetButton: evalResetSortButton,
    sortConfig: evalTabState.sort,
    validColumns: [...SORTABLE_CONTROL_COLUMNS, ...orderedEvalColumns, "eval_run_dir"],
    displayColumnName: displayEvalColumnName,
  });
  renderGroupByButtonState(
    {
      allButton: evalGroupByAllButton,
      toggleButton: evalGroupByToggleButton,
      noneButton: evalGroupByNoneButton,
    },
    orderedEvalColumns
  );
  renderStaticTabState({
    buttonElements: evalOptionsTabButtons,
    panelElements: evalOptionsTabPanels,
    activeValue: state.evalTabStates[state.activeEvalTab].activeOptionsTab,
    buttonAttribute: "data-eval-tab",
    panelAttribute: "data-eval-tab-panel",
  });
  const selectedEvaluationsForDefaults = getSelectedEvaluationGroups(evaluationContext).flatMap(
    (group) => group.evaluations
  );
  const evalDefaultColumns = getEvalColumnsWithMissingValues(
    selectedEvaluationsForDefaults,
    evalColumns
  );
  renderOptionsPanel({
    documentLike: document,
    checkboxListElement: evalTruncateColumnsList,
    checkboxColumns: [...new Set([...orderedEvalColumns, "eval_run_dir"])],
    checkedValues: evalTabState.truncateEnabledColumns,
    getCheckboxLabel: displayEvalColumnName,
    onCheckboxToggle: (column, checked) => {
      if (checked) {
        evalTabState.truncateEnabledColumns.add(column);
      } else {
        evalTabState.truncateEnabledColumns.delete(column);
      }
      renderEvaluations();
    },
    defaultsListElement: evalDefaultsList,
    defaultsPanelElement: evalDefaultsPanel,
    defaultColumns: evalDefaultColumns,
    getDefaultLabel: displayEvalColumnName,
    getDefaultValue: (column) => getEvalDefaultValue(evalTabState, column),
    getDefaultSuggestions: (column) =>
      getEvalDefaultSuggestions(selectedEvaluationsForDefaults, column),
    getDefaultMissingCount: (column) =>
      getEvalMissingValueCount(selectedEvaluationsForDefaults, column),
    inputIdPrefix: `eval-default-${state.activeEvalTab.replace(/[^a-zA-Z0-9_-]+/g, "-")}`,
    onDefaultCommit: (column, nextValue) => {
      setConfiguredDefault(evalTabState.defaultValues, column, nextValue);
      renderEvaluations();
    },
  });

  const displayedEvalGroups = getSortedEvaluationGroups(evaluationGroups, evalTabState);

  renderEvaluationTable({
    documentLike: document,
    tableElement: evaluationsTable,
    evalColumnSections,
    orderedEvalColumns,
    displayedGroups: displayedEvalGroups,
    evalTabState,
    displayColumnName: displayEvalColumnName,
    onSortToggle: setEvalSort,
    onToggleGroupByColumn: (column, checked) => {
      const next = new Set(evalTabState.groupByFields);
      if (checked) {
        next.add(column);
      } else {
        next.delete(column);
      }
      setActiveEvalGroupByFields(next);
    },
    onSelectAllDisplayed: (checked, displayedGroupIds) => {
      evalTabState.selectedGroupIds = checked ? new Set(displayedGroupIds) : new Set();
      renderEvaluations();
    },
    onGroupRowSelect: (groupId) => {
      if (evalTabState.selectedEvalGroupId === groupId) {
        evalTabState.selectedEvalGroupId = null;
      } else {
        evalTabState.selectedEvalGroupId = groupId;
        evalTabState.selectedEvalRunDir = null;
        state.activeEvalJsonTab = "evaluation";
      }
      renderEvaluations();
    },
    onToggleGroupExpansion: (groupId) => {
      if (evalTabState.expandedGroupIds.has(groupId)) {
        evalTabState.expandedGroupIds.delete(groupId);
      } else {
        evalTabState.expandedGroupIds.add(groupId);
      }
      renderEvaluations();
    },
    onToggleGroupSelection: (groupId, checked) => {
      if (checked) {
        evalTabState.selectedGroupIds.add(groupId);
      } else {
        evalTabState.selectedGroupIds.delete(groupId);
      }
      renderEvaluations();
    },
    onMemberRowSelect: (runDir) => {
      if (evalTabState.selectedEvalRunDir === runDir) {
        evalTabState.selectedEvalRunDir = null;
      } else {
        evalTabState.selectedEvalRunDir = runDir;
        evalTabState.selectedEvalGroupId = null;
        state.activeEvalJsonTab = "evaluation";
      }
      renderEvaluations();
    },
    getGroupValueDisplayFromEvaluations,
    getEvaluationEffectiveValue,
    getSortedEvaluations,
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });

  const selectedEvaluation = experimentEvaluations.find(
    (evaluation) => evaluation.runDir === evalTabState.selectedEvalRunDir
  ) || null;
  const selectedGroup = displayedEvalGroups.find(
    (group) => group.groupId === evalTabState.selectedEvalGroupId
  ) || null;
  renderEvalJsonPane({
    layoutElement: evalLayout,
    titleElement: evalJsonTitle,
    codeElement: evalJsonCode,
    evaluationButton: evalJsonTabEvaluation,
    predictionButton: evalJsonTabPrediction,
    activeTab: state.activeEvalJsonTab,
    selectedEvaluation,
    selectedGroup,
    getPredictionContent: reconstructPredictionContentForEvaluation,
  });

  updateStickyControlColumnOffsets(evaluationsTable);
  requestAnimationFrame(() => updateStickyControlColumnOffsets(evaluationsTable));

  const selectedEvaluationsCount = displayedEvalGroups
    .filter((group) => evalTabState.selectedGroupIds.has(group.groupId))
    .reduce((sum, group) => sum + group.evaluations.length, 0);
  const evalGroupByText = evalTabState.groupByFields.length
    ? evalTabState.groupByFields.map((field) => displayEvalColumnName(field)).join(", ")
    : "(none; one row per evaluation)";
  const predictionGroupByText = state.groupByFields.length
    ? state.groupByFields.map((field) => displayPredictionColumnName(field)).join(", ")
    : "(none)";
  evalSummary.textContent =
    `Selected evaluations: ${selectedEvaluationsCount} | Active tab: ${state.activeEvalTab} | Groups: ${displayedEvalGroups.length} | Group-by: ${evalGroupByText} (+ prediction group-by: ${predictionGroupByText})`;

  renderEvaluationPlots(state.activeEvalTab, evaluationContext);
}
