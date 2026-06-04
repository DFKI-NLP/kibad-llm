/**
 * TP/FP/FN collector plot aggregation and tab-map helpers.
 *
 * Data flow:
 * - Raw dashboard evaluations stay unchanged for tables and grouping.
 * - Plot code wraps each selected TP/FP/FN evaluation in one collection view.
 * - A `TpFpFnCollectorCollection` view exposes every top-level `data` field as
 *   `fields: Map<metric.field, collectorData>`.
 * - A single-field `TpFpFnCollector` view exposes exactly one field, resolved
 *   from `metric.field`, as `fields: Map<metric.field, evaluation.data>`.
 * - Tab construction derives available plot fields from collection-view field
 *   keys, and active plot aggregation reads `collection.fields.get(fieldLabel)`.
 *
 * The adapter is deliberately strict: missing `metric.field`, malformed metric
 * data, empty collection fields, and unsupported metric types throw early.
 */

import { formatRounded, interpolateColor, normalizeValue } from "../utils/values.js";
import {
  TP_FP_FN_KEYS,
  getGroupLabelForFields,
  getMetricCollectionView,
  getMetricPreparedDataContainer,
  getPlotDisplayLabel,
  isMetricDataRecord,
  plotSortCollator,
  scheduleAdaptiveSvgFit,
} from "./shared.js";
import { createPlotLegendElement } from "./legend.js";

/**
 * Builds a TP/FP/FN collection view for one evaluation.
 *
 * @param {object} evaluation - TP/FP/FN-like evaluation record.
 * @param {object} [options] - Field resolution helpers.
 * @returns {object} TP/FP/FN collection view.
 * @throws {Error} If the evaluation shape violates the TP/FP/FN contract.
 */
export function getTpFpFnCollectionView(evaluation, options = {}) {
  return getMetricCollectionView(evaluation, {
    collectionType: "TpFpFnCollectorCollection",
    singularType: "TpFpFnCollector",
    metricLabel: "TpFpFnCollector",
    ...options,
  });
}

/**
 * Builds TP/FP/FN collection views for a list of evaluations.
 *
 * @param {Array<object>} evaluations - Raw evaluation records.
 * @param {object} [options] - Field resolution helpers.
 * @returns {Array<object>} TP/FP/FN collection views.
 * @throws {Error} If any evaluation shape violates the TP/FP/FN contract.
 */
export function getTpFpFnCollectionViews(evaluations, options = {}) {
  return (evaluations || []).map((evaluation) => getTpFpFnCollectionView(evaluation, options));
}

/**
 * Converts an outcome key to its display label.
 *
 * @param {string} outcomeKey - Outcome key such as tp, fp, or fn.
 * @returns {string} Uppercase outcome label.
 */
export function getTpFpFnOutcomeLabel(outcomeKey) {
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

/**
 * Returns the heatmap color palette for a TP/FP/FN outcome.
 *
 * @param {string} outcomeKey - Outcome key such as tp, fp, or fn.
 * @returns {{start: Array<number>, end: Array<number>}} RGB interpolation endpoints.
 */
export function getTpFpFnPalette(outcomeKey) {
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

/**
 * Resolves the saturated display color for a TP/FP/FN outcome.
 *
 * @param {string} outcomeKey - Outcome key such as tp, fp, or fn.
 * @returns {string} CSS color string.
 */
export function getTpFpFnOutcomeColor(outcomeKey) {
  if (!outcomeKey) {
    return "#e2e8f0";
  }
  return interpolateColor(getTpFpFnPalette(outcomeKey).start, getTpFpFnPalette(outcomeKey).end, 1);
}

/**
 * Normalizes collector output into document ids mapped to tp/fp/fn label lists.
 *
 * @param {*} rawData - Collector data in per-document or global bucket form.
 * @returns {object} Normalized record map.
 * @throws {Error} If the collector data violates the TP/FP/FN data contract.
 */
export function normalizeTpFpFnCollectorData(rawData) {
  const result = {};

  const getRecordEntry = (recordId) => {
    const key = normalizeValue(recordId).trim();
    if (!key) {
      throw new Error("TpFpFnCollector data contains an empty record id.");
    }
    if (!result[key]) {
      result[key] = { tp: [], fp: [], fn: [] };
    }
    return result[key];
  };

  const appendUniqueValues = (target, bucket, values, context) => {
    if (values === undefined) {
      return;
    }
    if (!Array.isArray(values)) {
      throw new Error(`TpFpFnCollector ${context} bucket ${JSON.stringify(bucket)} must be an array.`);
    }
    const seen = new Set(target[bucket]);
    for (const [index, value] of values.entries()) {
      const normalized = normalizeValue(value).trim();
      if (!normalized) {
        throw new Error(`TpFpFnCollector ${context} bucket ${JSON.stringify(bucket)} contains an empty label at index ${index}.`);
      }
      if (seen.has(normalized)) {
        continue;
      }
      seen.add(normalized);
      target[bucket].push(normalized);
    }
    target[bucket].sort((a, b) => plotSortCollator.compare(a, b));
  };

  if (!rawData || typeof rawData !== "object" || Array.isArray(rawData)) {
    throw new Error("TpFpFnCollector data must be an object.");
  }

  const looksLikeGlobalOutput = TP_FP_FN_KEYS.some((bucket) => Array.isArray(rawData?.[bucket]));
  if (looksLikeGlobalOutput) {
    for (const bucket of TP_FP_FN_KEYS) {
      if (rawData[bucket] !== undefined && !Array.isArray(rawData[bucket])) {
        throw new Error(`TpFpFnCollector global bucket ${JSON.stringify(bucket)} must be an array.`);
      }
      const entries = rawData[bucket] || [];
      for (const [index, entry] of entries.entries()) {
        if (!Array.isArray(entry) || entry.length !== 2) {
          throw new Error(
            `TpFpFnCollector global bucket ${JSON.stringify(bucket)} entry ${index} must be a [record_id, label] array.`
          );
        }
        appendUniqueValues(getRecordEntry(entry[0]), bucket, [entry[1]], `global entry ${index}`);
      }
    }
    return result;
  }

  for (const [recordId, entry] of Object.entries(rawData)) {
    const normalizedRecordId = normalizeValue(recordId).trim();
    if (!normalizedRecordId) {
      throw new Error("TpFpFnCollector data contains an empty record id.");
    }
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
      throw new Error(`TpFpFnCollector record ${JSON.stringify(recordId)} must contain object bucket data.`);
    }
    const target = getRecordEntry(recordId);
    for (const bucket of TP_FP_FN_KEYS) {
      appendUniqueValues(target, bucket, entry[bucket], `record ${JSON.stringify(recordId)}`);
    }
  }

  return result;
}

/**
 * Resolves raw collector data for a normalized TP/FP/FN metric field.
 *
 * @param {object} evaluation - TP/FP/FN collection view or direct evaluation.
 * @param {string} normalizedFieldLabel - Normalized metric.field label.
 * @returns {object|undefined} Raw TP/FP/FN collector data for the field.
 * @throws {Error} If a collection view does not contain the requested field.
 */
function getTpFpFnFieldData(evaluation, normalizedFieldLabel) {
  if (evaluation?.fields instanceof Map) {
    if (!evaluation.fields.has(normalizedFieldLabel)) {
      throw new Error(`TpFpFnCollector collection view is missing metric field ${JSON.stringify(normalizedFieldLabel)}.`);
    }
    return evaluation.fields.get(normalizedFieldLabel);
  }
  return evaluation?.data;
}

/**
 * Lazily prepares one evaluation's TP/FP/FN data for aggregation.
 *
 * The prepared shape stores the document-label union and sparse outcome-state
 * lookup for one evaluation/field. Cross-run alignment and outcome counting
 * remain in `getTpFpFnCombinedAggregation()`.
 *
 * @param {object} evaluation - TP/FP/FN collection view or direct evaluation.
 * @param {string} normalizedFieldLabel - Normalized metric.field label.
 * @returns {{rowLabels: Set<string>, colLabels: Set<string>, cells: Map<string, object>}} Prepared per-evaluation data.
 * @throws {Error} If the requested field data violates the TP/FP/FN collector contract.
 */
function prepareTpFpFnEvaluationData(evaluation, normalizedFieldLabel) {
  const cache = getMetricPreparedDataContainer(evaluation);
  if (cache && Object.hasOwn(cache, normalizedFieldLabel)) {
    return cache[normalizedFieldLabel];
  }

  const rawData = getTpFpFnFieldData(evaluation, normalizedFieldLabel);
  if (!isMetricDataRecord(rawData)) {
    throw new Error(`TpFpFnCollector field ${JSON.stringify(normalizedFieldLabel)} must contain object metric data.`);
  }

  const rowLabels = new Set();
  const colLabels = new Set();
  const cells = new Map();
  const normalizedData = normalizeTpFpFnCollectorData(rawData);
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
      cells.set(`${recordId}|#|${label}`, rowState);
    }
  }

  const prepared = { rowLabels, colLabels, cells };
  if (cache) {
    cache[normalizedFieldLabel] = prepared;
  }
  return prepared;
}

/**
 * Aggregates one TP/FP/FN collector field across collection views.
 *
 * @param {Array<object>} experimentEvaluations - TP/FP/FN collection views.
 * @param {string} fieldLabel - Metric field to aggregate.
 * @returns {object} Aggregated rows, columns, cell states, counts, and evaluation labels.
 */
export function getTpFpFnCombinedAggregation(experimentEvaluations, fieldLabel) {
  const normalizedFieldLabel = normalizeValue(fieldLabel).trim();
  if (!normalizedFieldLabel) {
    throw new Error("TpFpFnCollector aggregation requires a non-empty metric field.");
  }
  const rowLabels = new Set();
  const colLabels = new Set();
  const evaluationCells = [];
  const evaluationLabels = [];

  for (const [evaluationIndex, evaluation] of experimentEvaluations.entries()) {
    evaluationLabels.push(normalizeValue(evaluation?.runDir) || `evaluation ${evaluationIndex + 1}`);
    const prepared = prepareTpFpFnEvaluationData(evaluation, normalizedFieldLabel);
    for (const recordId of prepared.rowLabels) {
      rowLabels.add(recordId);
    }
    for (const label of prepared.colLabels) {
      colLabels.add(label);
    }
    evaluationCells.push(prepared.cells);
  }

  const rows = Array.from(rowLabels).sort((a, b) => plotSortCollator.compare(a, b));
  const cols = Array.from(colLabels).sort((a, b) => plotSortCollator.compare(a, b));
  const cells = new Map();

  for (const row of rows) {
    for (const col of cols) {
      const key = `${row}|#|${col}`;
      // Align this document/label cell across all selected runs. Missing cells
      // become an all-false state, so they count as "empty" instead of TP/FP/FN.
      const rowStates = evaluationCells.map(
        (cellMap) => cellMap.get(key) || { tp: false, fp: false, fn: false }
      );
      const counts = { tp: 0, fp: 0, fn: 0, empty: 0 };
      // Counts are raw run counts: how many selected evaluations marked this
      // document/label as TP, FP, FN, or none of them.
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

/**
 * Filters TP/FP/FN rows and columns by document and label totals.
 *
 * @param {object} aggregation - Combined TP/FP/FN aggregation.
 * @param {number} minLabelTotal - Minimum column total to keep.
 * @param {number} minDocumentTotal - Minimum row total to keep.
 * @returns {object} Filtered aggregation with totals.
 */
export function filterTpFpFnAggregationByTotals(aggregation, minLabelTotal, minDocumentTotal) {
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

/**
 * Builds TP/FP/FN plot tabs grouped by metric field or plot group.
 *
 * @param {object} options - Plot groups, evaluations, tab mode, and label helpers.
 * @returns {Map<string, object>} Tab map with labels and plot definitions.
 */
export function buildTpFpFnTabMap({
  plotGroups,
  labelFields,
  evalTabState,
  confusionTabsBy,
  getEvaluationEffectiveValue,
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
      collections: getTpFpFnCollectionViews(group.evaluations, collectionViewOptions),
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
      .sort(([a], [b]) => plotSortCollator.compare(a, b))
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
 * Builds tooltip lines and copyable JSON payload for a TP/FP/FN matrix cell.
 *
 * @param {string} row - Document id.
 * @param {string} col - Label value.
 * @param {object} stats - Aggregated cell stats.
 * @param {number} totalEvaluations - Number of evaluations in the aggregation.
 * @param {Array<string>} evaluationLabels - Labels for each evaluation.
 * @param {number} precision - Decimal precision for displayed percentages.
 * @returns {{lines: Array<string>, payload: object}} Tooltip text and JSON payload.
 */
export function buildTpFpFnCellSummary(row, col, stats, totalEvaluations, evaluationLabels, precision) {
  // Percentages normalize raw TP/FP/FN counts by the number of selected
  // evaluations, not by the number of non-empty cells. Empty runs remain in the
  // denominator, so TP + FP + FN can be below 100%.
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

/**
 * Creates the shared TP/FP/FN legend element.
 *
 * @param {object} [options] - DOM dependency override.
 * @returns {HTMLElement} Legend element with TP, FP, and FN items.
 */
export function createTpFpFnLegendElement({ documentLike = globalThis.document } = {}) {
  return createPlotLegendElement({
    documentLike,
    legendItems: [
      { label: "TP", color: getTpFpFnOutcomeColor("tp") },
      { label: "FP", color: getTpFpFnOutcomeColor("fp") },
      { label: "FN", color: getTpFpFnOutcomeColor("fn") },
    ],
  });
}

/**
 * Creates an SVG matrix showing TP/FP/FN shares per document/label cell.
 *
 * @param {object} options - Aggregation, precision, tooltip handlers, clipboard writer, and DOM dependencies.
 * @returns {SVGSVGElement} Rendered combined TP/FP/FN matrix SVG.
 */
export function createTpFpFnCombinedMatrixSvg({
  documentLike = globalThis.document,
  requestAnimationFrameLike = globalThis.requestAnimationFrame,
  aggregation,
  precision,
  getDisplayLabel = (label) => label,
  showTooltip,
  moveTooltip,
  hideTooltip,
  writeTextToClipboard,
  consoleLike = globalThis.console,
}) {
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

  const svg = documentLike.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const contentGroup = documentLike.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(contentGroup);

  const xAxisTitle = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
  xAxisTitle.setAttribute("x", String(margin.left + (cols.length * cellWidth) / 2));
  xAxisTitle.setAttribute("y", "20");
  xAxisTitle.setAttribute("text-anchor", "middle");
  xAxisTitle.setAttribute("fill", "currentColor");
  xAxisTitle.setAttribute("font-size", "13");
  xAxisTitle.textContent = "Label";
  contentGroup.appendChild(xAxisTitle);

  const yAxisTitle = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
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
    const label = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
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
    const label = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(x + 2));
    label.setAttribute("y", String(y));
    label.setAttribute("transform", `rotate(-35 ${x + 2} ${y})`);
    label.setAttribute("text-anchor", "start");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = getDisplayLabel(col);
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

      const cellBorder = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
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
        // Mini-cell color intensity uses the same normalization as the tooltip:
        // count for this outcome divided by all selected evaluations.
        const share = totalEvaluations ? stats.counts[outcomeKey] / totalEvaluations : 0;
        const palette = getTpFpFnPalette(outcomeKey);
        const rect = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
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

      const overlay = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
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
        showTooltip(event, summary.lines);
      });
      overlay.addEventListener("mousemove", moveTooltip);
      overlay.addEventListener("mouseout", hideTooltip);
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
          showTooltip(event, [...summary.lines, "", "Copied JSON to clipboard."]);
        } catch (error) {
          consoleLike?.warn?.("Failed to copy TpFpFn cell summary to clipboard.", error);
          showTooltip(event, [...summary.lines, "", "Copy to clipboard failed."]);
        }
      });
      contentGroup.appendChild(overlay);
    });
  });

  scheduleAdaptiveSvgFit({ documentLike, requestAnimationFrameLike, svg, contentGroup, minWidth: width, minHeight: height });
  return svg;
}
