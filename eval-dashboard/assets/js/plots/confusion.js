/**
 * Confusion-matrix plot helpers for collection wrapping, aggregation, tab maps,
 * download inputs, and SVG rendering.
 *
 * This file exists to keep confusion-specific matrix behavior out of the
 * dashboard controller and out of generic plot helpers. It normalizes single
 * and collection metrics into one field-map contract, then shares the same
 * pre-aggregation inputs between rendering and downloaded plot data.
 */

import { formatRounded, interpolateColor, meanAndStd, normalizeValue } from "../utils/values.js";
import { getEvaluationRunId } from "../utils/runs.js";
import {
  assertAlignedArrayLengths,
  getMetricCollectionView,
  getMetricPreparedDataContainer,
  getRequiredPlotRunId,
  isMetricDataRecord,
} from "./shared.js";
import {
  assertMatrixLabelExcludesKeyDelimiter,
  buildMatrixTabMap,
  getMatrixCellKey,
} from "./shared-matrix.js";

/**
 * Builds confusion-matrix collection views for a list of evaluations.
 *
 * Confusion plots can receive either collection metrics with many fields or
 * single-field metrics resolved through `metric.field`. Wrapping both shapes in
 * the shared collection-view contract lets tab construction and aggregation use
 * one `fields` map path.
 *
 * @param {Array<object>} evaluations - Raw evaluation records.
 * @param {object} [options] - Field resolution helpers.
 * @returns {Array<object>} Confusion matrix collection views.
 * @throws {Error} If any evaluation shape violates the confusion-matrix contract.
 */
export function getConfusionMatrixCollectionViews(evaluations, options = {}) {
  return (evaluations || []).map((evaluation) => getMetricCollectionView(evaluation, {
    collectionType: "ConfusionMatrixCollection",
    singularType: "ConfusionMatrix",
    metricLabel: "ConfusionMatrix",
    ...options,
  }));
}

/**
 * Counts distinct source runs represented by confusion-matrix evaluations.
 *
 * Tab labels use source-run counts rather than collection-view counts so a
 * collection metric and its wrapped view still represent one evaluation run.
 *
 * @param {Array<object>} evaluations - Evaluation records.
 * @returns {number} Number of unique semantic run ids.
 */
export function countDistinctConfusionMatrixRuns(evaluations) {
  return new Set(
    (evaluations || [])
      .map((evaluation) => getEvaluationRunId(evaluation?.evaluation || evaluation))
      .filter(Boolean)
  ).size;
}

/**
 * Resolves raw matrix data for a normalized confusion metric field.
 *
 * Aggregation code works with collection views and direct evaluations. This
 * helper keeps the field lookup and missing-field error in one place before the
 * raw matrix shape is validated.
 *
 * @param {object} evaluation - Confusion collection view or direct evaluation.
 * @param {string} normalizedFieldLabel - Normalized metric.field label.
 * @returns {object|undefined} Raw confusion matrix data for the field.
 * @throws {Error} If a collection view does not contain the requested field.
 */
function getConfusionMatrixFieldData(evaluation, normalizedFieldLabel) {
  if (evaluation?.fields instanceof Map) {
    if (!evaluation.fields.has(normalizedFieldLabel)) {
      throw new Error(`ConfusionMatrix collection view is missing metric field ${JSON.stringify(normalizedFieldLabel)}.`);
    }
    return evaluation.fields.get(normalizedFieldLabel);
  }
  return evaluation?.data;
}

/**
 * Lazily prepares one evaluation's confusion data for aggregation.
 *
 * The prepared shape stores the row-label union, column-label union, and sparse
 * cell lookup for one evaluation/field. Later helpers handle cross-run
 * alignment and mean/std aggregation.
 * Caching this per evaluation avoids rebuilding sparse maps when tab maps,
 * download payloads, or filters are recomputed.
 *
 * @param {object} evaluation - Confusion collection view or direct evaluation.
 * @param {string} normalizedFieldLabel - Normalized metric.field label.
 * @returns {{rowLabels: Set<string>, colLabels: Set<string>, cells: Map<string, number>}} Prepared per-evaluation data.
 * @throws {Error} If the requested field data violates the confusion matrix contract.
 */
function prepareConfusionMatrixEvaluationData(evaluation, normalizedFieldLabel) {
  const cache = getMetricPreparedDataContainer(evaluation);
  if (cache && Object.hasOwn(cache, normalizedFieldLabel)) {
    return cache[normalizedFieldLabel];
  }

  const evalData = getConfusionMatrixFieldData(evaluation, normalizedFieldLabel);
  if (!isMetricDataRecord(evalData)) {
    throw new Error(`ConfusionMatrix field ${JSON.stringify(normalizedFieldLabel)} must contain object metric data.`);
  }

  const rowLabels = new Set();
  const colLabels = new Set();
  const cells = new Map();
  // The raw matrix shape is actual label -> predicted label -> count.
  for (const [actualLabel, predictedMap] of Object.entries(evalData)) {
    const normalizedActualLabel = normalizeValue(actualLabel).trim();
    if (!normalizedActualLabel) {
      throw new Error(`ConfusionMatrix field ${JSON.stringify(normalizedFieldLabel)} contains an empty actual label.`);
    }
    assertMatrixLabelExcludesKeyDelimiter(
      actualLabel,
      `ConfusionMatrix field ${JSON.stringify(normalizedFieldLabel)} actual label ${JSON.stringify(actualLabel)}`
    );
    if (!isMetricDataRecord(predictedMap)) {
      throw new Error(
        `ConfusionMatrix field ${JSON.stringify(normalizedFieldLabel)} actual label ${JSON.stringify(actualLabel)} must map to object predicted-label data.`
      );
    }
    for (const [predictedLabel, rawValue] of Object.entries(predictedMap)) {
      const normalizedPredictedLabel = normalizeValue(predictedLabel).trim();
      if (!normalizedPredictedLabel) {
        throw new Error(
          `ConfusionMatrix field ${JSON.stringify(normalizedFieldLabel)} actual label ${JSON.stringify(actualLabel)} contains an empty predicted label.`
        );
      }
      if (!colLabels.has(predictedLabel)) {
        assertMatrixLabelExcludesKeyDelimiter(
          predictedLabel,
          `ConfusionMatrix field ${JSON.stringify(normalizedFieldLabel)} predicted label ${JSON.stringify(predictedLabel)}`
        );
        colLabels.add(predictedLabel);
      }
      if (!Number.isFinite(rawValue)) {
        throw new Error(
          `ConfusionMatrix field ${JSON.stringify(normalizedFieldLabel)} cell ${JSON.stringify(actualLabel)} -> ${JSON.stringify(predictedLabel)} must be a finite number.`
        );
      }
      rowLabels.add(actualLabel);
      cells.set(getMatrixCellKey(actualLabel, predictedLabel), Number(rawValue));
    }
  }

  const prepared = { rowLabels, colLabels, cells };
  if (cache) {
    cache[normalizedFieldLabel] = prepared;
  }
  return prepared;
}

/**
 * Sorts labels deterministically while keeping sentinel labels at the end.
 *
 * Confusion matrices use special row/column labels for unassigned or
 * undetected cases. Keeping those labels last makes the heatmap easier to scan
 * without changing ordinary locale sorting for real labels.
 *
 * @param {Iterable<string>} values - Labels to sort.
 * @param {string} forcedLast - Sentinel label that should sort last.
 * @returns {Array<string>} Sorted labels.
 */
function sortWithForcedLast(values, forcedLast) {
  return Array.from(values).sort((a, b) => {
    if (a === forcedLast && b !== forcedLast) {
      return 1;
    }
    if (b === forcedLast && a !== forcedLast) {
      return -1;
    }
    return a.localeCompare(b);
  });
}

/**
 * Builds aligned per-evaluation inputs for confusion-matrix aggregation.
 *
 * Rendering and data download both need the same normalized rows, columns, and
 * sparse per-evaluation cells. Keeping that setup here prevents a separate
 * download path from re-preparing confusion data.
 * The returned input is the shared pre-aggregation boundary.
 *
 * @param {Array<object>} experimentEvaluations - Confusion matrix collection views.
 * @param {string} fieldLabel - Metric field to align.
 * @returns {{rows: Array<string>, cols: Array<string>, runIds: Array<string>, runDirs: Array<string>, cells: Array<Map<string, number>>}} Aligned aggregation inputs.
 */
export function getConfusionMatrixAggregationInput(experimentEvaluations, fieldLabel) {
  const normalizedFieldLabel = normalizeValue(fieldLabel).trim();
  if (!normalizedFieldLabel) {
    throw new Error("ConfusionMatrix aggregation requires a non-empty metric field.");
  }
  const rowLabels = new Set();
  const colLabels = new Set();
  const runIds = [];
  const runDirs = [];
  const cells = [];

  for (const evaluation of experimentEvaluations) {
    const prepared = prepareConfusionMatrixEvaluationData(evaluation, normalizedFieldLabel);
    // Keep the union of labels seen in any run so absent cells can still be
    // represented as zero during the later mean/std calculation.
    for (const actualLabel of prepared.rowLabels) {
      rowLabels.add(actualLabel);
    }
    for (const predictedLabel of prepared.colLabels) {
      colLabels.add(predictedLabel);
    }
    // Store this run's sparse cell map as one sample in the cross-run
    // aggregation.
    runIds.push(getRequiredPlotRunId(evaluation, "ConfusionMatrix aggregation"));
    runDirs.push(evaluation?.runDir || "");
    cells.push(prepared.cells);
  }
  assertAlignedArrayLengths(
    "ConfusionMatrix aggregation",
    "runIds",
    runIds,
    "cells",
    cells
  );
  assertAlignedArrayLengths(
    "ConfusionMatrix aggregation",
    "runDirs",
    runDirs,
    "cells",
    cells
  );

  const rows = sortWithForcedLast(rowLabels, "UNASSIGNABLE");
  const cols = sortWithForcedLast(colLabels, "UNDETECTED");
  return { rows, cols, runIds, runDirs, cells };
}

/**
 * Aggregates aligned confusion-matrix inputs into mean/std values.
 *
 * This lets callers reuse the already-prepared aggregation input for rendering
 * and download data instead of running the per-evaluation preparation twice.
 * Missing sparse cells contribute zero so each visible cell is aligned across
 * the same evaluation count.
 *
 * @param {object} aggregationInput - Output of getConfusionMatrixAggregationInput.
 * @returns {{rows: Array<string>, cols: Array<string>, cells: Map<string, object>}} Aggregated matrix.
 */
export function getConfusionMatrixAggregationFromInput(aggregationInput) {
  const { rows, cols, runIds, runDirs, cells: inputCells } = aggregationInput;
  assertAlignedArrayLengths(
    "ConfusionMatrix aggregation input",
    "runIds",
    runIds,
    "cells",
    inputCells
  );
  assertAlignedArrayLengths(
    "ConfusionMatrix aggregation input",
    "runDirs",
    runDirs,
    "cells",
    inputCells
  );
  const aggregatedCells = new Map();
  for (const row of rows) {
    for (const col of cols) {
      const key = getMatrixCellKey(row, col);
      // Each confusion-matrix cell is aligned across all selected runs. If a
      // run has no explicit count for this actual/predicted pair, it
      // contributes 0 before computing the aggregate.
      const values = inputCells.map((cellMap) => cellMap.get(key) ?? 0);
      // The displayed value is the population mean and population standard
      // deviation of those aligned per-run counts.
      const stats = meanAndStd(values) || { mean: 0, std: 0 };
      aggregatedCells.set(key, stats);
    }
  }

  return { rows, cols, cells: aggregatedCells };
}

/**
 * Removes matrix rows and columns whose mean totals are below a threshold.
 *
 * Row and column filtering is iterative because dropping a low-total row can
 * also lower column totals, and vice versa. The resulting matrix matches the
 * visible heatmap while preserving totals for labels that remain.
 *
 * @param {object} aggregation - Confusion matrix aggregation.
 * @param {number} minLabelTotal - Minimum row/column total to keep.
 * @returns {object} Filtered aggregation with totals.
 */
export function filterConfusionMatrixAggregationByLabelTotal(aggregation, minLabelTotal) {
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
        filteredCols.reduce((sum, col) => sum + (cells.get(getMatrixCellKey(row, col))?.mean ?? 0), 0),
      ])
    );
    colTotals = new Map(
      filteredCols.map((col) => [
        col,
        filteredRows.reduce((sum, row) => sum + (cells.get(getMatrixCellKey(row, col))?.mean ?? 0), 0),
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
      filteredCols.reduce((sum, col) => sum + (cells.get(getMatrixCellKey(row, col))?.mean ?? 0), 0),
    ])
  );
  colTotals = new Map(
    filteredCols.map((col) => [
      col,
      filteredRows.reduce((sum, row) => sum + (cells.get(getMatrixCellKey(row, col))?.mean ?? 0), 0),
    ])
  );

  const filteredCells = new Map();
  for (const row of filteredRows) {
    for (const col of filteredCols) {
      const key = getMatrixCellKey(row, col);
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

/**
 * Builds confusion-matrix plot tabs grouped by metric field or plot group.
 *
 * The dashboard supports two views of the same collection data: metric-field
 * tabs compare plot groups for one field, while prediction-group tabs compare
 * fields inside one plot group. This helper centralizes that tab-map shape so
 * rendering and download selection use the same active plot definitions.
 *
 * @param {object} options - Plot groups, evaluations, tab mode, and label helpers.
 * @returns {Map<string, object>} Tab map with labels and plot definitions.
 */
export function buildConfusionTabMap({
  activeExperiment,
  plotGroups,
  labelFields,
  evalTabState,
  matrixTabsBy,
  getEvaluationEffectiveValue,
  getEvaluationExperiment,
  displayPlotGroupFieldName,
  shortenLabels = false,
}) {
  return buildMatrixTabMap({
    plotGroups,
    labelFields,
    evalTabState,
    matrixTabsBy,
    getEvaluationEffectiveValue,
    displayPlotGroupFieldName,
    shortenLabels,
    getCollectionViews: getConfusionMatrixCollectionViews,
    filterEvaluations: (evaluations) =>
      evaluations.filter((evaluation) => getEvaluationExperiment(evaluation) === activeExperiment),
  });
}

/**
 * Creates an SVG heatmap for an aggregated confusion matrix.
 *
 * The renderer receives already-filtered mean/std cells and is dependency
 * injected for tests. Tooltips expose the exact actual/predicted label pair and
 * aggregated values without coupling SVG rendering to data preparation.
 *
 * @param {object} options - Aggregation, precision, label formatter, and tooltip handlers.
 * @returns {SVGSVGElement} Rendered heatmap SVG.
 */
export function createConfusionMatrixHeatmapSvg({
  documentLike = globalThis.document,
  aggregation,
  precision,
  getDisplayLabel = (label) => label,
  showTooltip,
  moveTooltip,
  hideTooltip,
}) {
  const { rows, cols, cells } = aggregation;
  const cellSize = 96;
  const margin = { top: 130, right: 20, bottom: 20, left: 280 };
  const width = margin.left + cols.length * cellSize + margin.right;
  const height = margin.top + rows.length * cellSize + margin.bottom;
  const maxMean = Math.max(0, ...Array.from(cells.values()).map((cell) => cell.mean));

  const svg = documentLike.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const xAxisTitle = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
  xAxisTitle.setAttribute("x", String(margin.left + (cols.length * cellSize) / 2));
  xAxisTitle.setAttribute("y", "20");
  xAxisTitle.setAttribute("text-anchor", "middle");
  xAxisTitle.setAttribute("fill", "currentColor");
  xAxisTitle.setAttribute("font-size", "13");
  xAxisTitle.textContent = "Predicted label";
  svg.appendChild(xAxisTitle);

  const yAxisTitle = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
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
    const label = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 10));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = getDisplayLabel(row);
    svg.appendChild(label);
  });

  rows.forEach((row, rowIndex) => {
    cols.forEach((col, colIndex) => {
      const key = getMatrixCellKey(row, col);
      const stats = cells.get(key) || { mean: 0, std: 0 };
      const x = margin.left + colIndex * cellSize;
      const y = margin.top + rowIndex * cellSize;
      const t = maxMean > 0 ? stats.mean / maxMean : 0;
      const fill = interpolateColor([247, 251, 255], [8, 48, 107], t);

      const rect = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", String(x));
      rect.setAttribute("y", String(y));
      rect.setAttribute("width", String(cellSize));
      rect.setAttribute("height", String(cellSize));
      rect.setAttribute("fill", fill);
      rect.setAttribute("stroke", "#33415555");
      rect.setAttribute("stroke-width", "1");
      rect.style.cursor = "crosshair";
      rect.addEventListener("mouseover", (event) => {
        showTooltip(event, [
          `actual:    ${row}`,
          `predicted: ${col}`,
          `mean: ${formatRounded(stats.mean, precision)}`,
          `std:  ${formatRounded(stats.std, precision)}`,
        ]);
      });
      rect.addEventListener("mousemove", moveTooltip);
      rect.addEventListener("mouseout", hideTooltip);
      svg.appendChild(rect);

      const text = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", String(x + cellSize / 2));
      text.setAttribute("y", String(y + cellSize / 2 + 4));
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("fill", t > 0.55 ? "#f8fafc" : "#0f172a");
      text.setAttribute("font-size", "11");
      text.textContent = `${formatRounded(stats.mean, precision)}±${formatRounded(stats.std, precision)}`;
      svg.appendChild(text);
    });
  });

  cols.forEach((col, colIndex) => {
    const x = margin.left + colIndex * cellSize + cellSize / 2;
    const label = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    const y = margin.top - 10;
    label.setAttribute("x", String(x + 2));
    label.setAttribute("y", String(y));
    label.setAttribute("transform", `rotate(-35 ${x + 2} ${y})`);
    label.setAttribute("text-anchor", "start");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = getDisplayLabel(col);
    svg.appendChild(label);
  });

  return svg;
}
