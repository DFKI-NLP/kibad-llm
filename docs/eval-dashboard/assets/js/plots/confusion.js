/**
 * Confusion-matrix plot aggregation and tab-map helpers.
 *
 * Data flow:
 * - Raw dashboard evaluations stay unchanged for tables and grouping.
 * - Plot code wraps each selected confusion evaluation in one collection view.
 * - A `ConfusionMatrixCollection` view exposes every top-level `data` field as
 *   `fields: Map<metric.field, matrixData>`.
 * - A single-field `ConfusionMatrix` view exposes exactly one field, resolved
 *   from `metric.field`, as `fields: Map<metric.field, evaluation.data>`.
 * - Tab construction derives available plot fields from collection-view field
 *   keys, and active plot aggregation reads `collection.fields.get(fieldLabel)`.
 *
 * The adapter is deliberately strict: missing `metric.field`, malformed metric
 * data, empty collection fields, and unsupported metric types throw early.
 */

import { formatRounded, interpolateColor, meanAndStd, normalizeValue } from "../utils/values.js";
import {
  getMetricCollectionSourceRunDir,
  getMetricCollectionView,
  getMetricPreparedDataContainer,
  getGroupLabelForFields,
  getPlotDisplayLabel,
  isMetricDataRecord,
} from "./shared.js";

/**
 * Builds a confusion-matrix collection view for one evaluation.
 *
 * @param {object} evaluation - Confusion-matrix-like evaluation record.
 * @param {object} [options] - Field resolution helpers.
 * @returns {object} Confusion matrix collection view.
 * @throws {Error} If the evaluation shape violates the confusion-matrix contract.
 */
export function getConfusionMatrixCollectionView(evaluation, options = {}) {
  return getMetricCollectionView(evaluation, {
    collectionType: "ConfusionMatrixCollection",
    singularType: "ConfusionMatrix",
    metricLabel: "ConfusionMatrix",
    ...options,
  });
}

/**
 * Builds confusion-matrix collection views for a list of evaluations.
 *
 * @param {Array<object>} evaluations - Raw evaluation records.
 * @param {object} [options] - Field resolution helpers.
 * @returns {Array<object>} Confusion matrix collection views.
 * @throws {Error} If any evaluation shape violates the confusion-matrix contract.
 */
export function getConfusionMatrixCollectionViews(evaluations, options = {}) {
  return (evaluations || []).map((evaluation) => getConfusionMatrixCollectionView(evaluation, options));
}

/**
 * Counts distinct source runs represented by confusion-matrix evaluations.
 *
 * @param {Array<object>} evaluations - Evaluation records.
 * @returns {number} Number of unique non-empty source run directories.
 */
export function countDistinctConfusionMatrixRuns(evaluations) {
  return new Set(
    (evaluations || [])
      .map((evaluation) => evaluation?.sourceRunDir || getMetricCollectionSourceRunDir(evaluation?.evaluation || evaluation))
      .filter(Boolean)
  ).size;
}

/**
 * Builds the display title for a confusion matrix plot group.
 *
 * @param {object} options - Evaluations, tab state, value resolver, and label options.
 * @returns {string} Title describing the selected metric.field values.
 */
export function getConfusionMatrixTitle({
  experimentEvaluations,
  evalTabState,
  getEvaluationEffectiveValue,
  shortenLabels = false,
}) {
  const fieldValues = new Set();
  for (const evaluation of experimentEvaluations || []) {
    if (evaluation?.fields instanceof Map) {
      for (const fieldLabel of evaluation.fields.keys()) {
        fieldValues.add(fieldLabel);
      }
      continue;
    }
    const value = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
    if (value) {
      fieldValues.add(value);
    }
  }
  if (fieldValues.size === 0) {
    throw new Error("ConfusionMatrix title requires at least one metric.field.");
  }
  if (fieldValues.size === 1) {
    return getPlotDisplayLabel(Array.from(fieldValues)[0], { shortenLabels });
  }
  return `mixed metric.field: ${Array.from(fieldValues)
    .sort((a, b) => a.localeCompare(b))
    .map((value) => getPlotDisplayLabel(value, { shortenLabels }))
    .join(", ")}`;
}


/**
 * Resolves raw matrix data for a normalized confusion metric field.
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
 * cell lookup for one evaluation/field. Cross-run alignment and mean/std
 * aggregation remain in `getConfusionMatrixAggregation()`.
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
      if (!Number.isFinite(rawValue)) {
        throw new Error(
          `ConfusionMatrix field ${JSON.stringify(normalizedFieldLabel)} cell ${JSON.stringify(actualLabel)} -> ${JSON.stringify(predictedLabel)} must be a finite number.`
        );
      }
      rowLabels.add(actualLabel);
      colLabels.add(predictedLabel);
      cells.set(`${actualLabel}|#|${predictedLabel}`, Number(rawValue));
    }
  }

  const prepared = { rowLabels, colLabels, cells };
  if (cache) {
    cache[normalizedFieldLabel] = prepared;
  }
  return prepared;
}

/**
 * Aggregates one confusion-matrix field across collection views into mean/std values.
 *
 * @param {Array<object>} experimentEvaluations - Confusion matrix collection views.
 * @param {string} fieldLabel - Metric field to aggregate.
 * @returns {{rows: Array<string>, cols: Array<string>, cells: Map<string, object>}} Aggregated matrix.
 */
export function getConfusionMatrixAggregation(experimentEvaluations, fieldLabel) {
  const normalizedFieldLabel = normalizeValue(fieldLabel).trim();
  if (!normalizedFieldLabel) {
    throw new Error("ConfusionMatrix aggregation requires a non-empty metric field.");
  }
  const rowLabels = new Set();
  const colLabels = new Set();
  const evaluationCells = [];

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
    evaluationCells.push(prepared.cells);
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
      // Each confusion-matrix cell is aligned across all selected runs. If a
      // run has no explicit count for this actual/predicted pair, it
      // contributes 0 before computing the aggregate.
      const values = evaluationCells.map((cellMap) => cellMap.get(key) ?? 0);
      // The displayed value is the population mean and population standard
      // deviation of those aligned per-run counts.
      const stats = meanAndStd(values) || { mean: 0, std: 0 };
      cells.set(key, stats);
    }
  }

  return { rows, cols, cells };
}

/**
 * Removes matrix rows and columns whose mean totals are below a threshold.
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

/**
 * Builds confusion-matrix plot tabs grouped by metric field or plot group.
 *
 * @param {object} options - Plot groups, evaluations, tab mode, and label helpers.
 * @returns {Map<string, object>} Tab map with labels and plot definitions.
 */
export function buildConfusionTabMap({
  activeExperiment,
  plotGroups,
  labelFields,
  evalTabState,
  confusionTabsBy,
  getEvaluationEffectiveValue,
  getEvaluationExperiment,
  displayPlotGroupFieldName,
  shortenLabels = false,
}) {
  const tabMap = new Map();
  const collectionViewOptions = { evalTabState, getEvaluationEffectiveValue };
  const groupEntries = plotGroups
    .map((group, index) => ({
      key: `group|#|${group.groupId}`,
      label: getGroupLabelForFields(
        group,
        labelFields,
        `group ${index + 1}`,
        displayPlotGroupFieldName
      ),
      collections: getConfusionMatrixCollectionViews(
        group.evaluations.filter((evaluation) => getEvaluationExperiment(evaluation) === activeExperiment),
        collectionViewOptions
      ),
    }))
    .filter((entry) => entry.collections.length > 0);

  if (confusionTabsBy === "metric_field") {
    for (const groupEntry of groupEntries) {
      const byField = new Map();
      for (const collection of groupEntry.collections) {
        for (const fieldLabel of collection.fields.keys()) {
          if (!tabMap.has(fieldLabel)) {
            tabMap.set(fieldLabel, {
              label: getPlotDisplayLabel(fieldLabel, { shortenLabels }),
              plots: [],
            });
          }
          if (!byField.has(fieldLabel)) {
            byField.set(fieldLabel, []);
          }
          byField.get(fieldLabel).push(collection);
        }
      }
      for (const [fieldKey, collectionsForFieldAndGroup] of byField.entries()) {
        const tab = tabMap.get(fieldKey);
        if (!tab || collectionsForFieldAndGroup.length === 0) {
          continue;
        }
        tab.plots.push({
          label: groupEntry.label,
          fieldLabel: fieldKey,
          collections: collectionsForFieldAndGroup,
        });
      }
    }
    return tabMap;
  }

  for (const groupEntry of groupEntries) {
    const byField = new Map();
    for (const collection of groupEntry.collections) {
      for (const fieldLabel of collection.fields.keys()) {
        if (!byField.has(fieldLabel)) {
          byField.set(fieldLabel, []);
        }
        byField.get(fieldLabel).push(collection);
      }
    }
    const plots = Array.from(byField.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([fieldLabel, collections]) => ({
        label: fieldLabel,
        fieldLabel,
        collections,
      }));
    tabMap.set(groupEntry.key, { label: groupEntry.label, plots });
  }

  return tabMap;
}

/**
 * Creates an SVG heatmap for an aggregated confusion matrix.
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
      const key = `${row}|#|${col}`;
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
