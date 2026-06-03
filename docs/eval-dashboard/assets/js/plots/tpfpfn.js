/**
 * TP/FP/FN collector plot aggregation and tab-map helpers.
 */

import { formatRounded, interpolateColor, normalizeValue } from "../utils/values.js";
import {
  TP_FP_FN_KEYS,
  getGroupLabelForFields,
  getPlotDisplayLabel,
  plotSortCollator,
  scheduleAdaptiveSvgFit,
} from "./shared.js";
import { expandMetricFieldCollectionEvaluation } from "./confusion.js";
import { createPlotLegendElement } from "./legend.js";

export function expandTpFpFnLikeEvaluation(evaluation) {
  return expandMetricFieldCollectionEvaluation(evaluation, {
    collectionType: "TpFpFnCollectorCollection",
    singularType: "TpFpFnCollector",
    fallbackRunDirPrefix: "tpfpfn-field",
  });
}

export function normalizeTpFpFnLikeEvaluations(evaluations) {
  return (evaluations || []).flatMap((evaluation) => expandTpFpFnLikeEvaluation(evaluation));
}

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

export function getTpFpFnOutcomeColor(outcomeKey) {
  if (!outcomeKey) {
    return "#e2e8f0";
  }
  return interpolateColor(getTpFpFnPalette(outcomeKey).start, getTpFpFnPalette(outcomeKey).end, 1);
}

export function normalizeTpFpFnCollectorData(rawData) {
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
    target[bucket].sort((a, b) => plotSortCollator.compare(a, b));
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

export function getTpFpFnCombinedAggregation(experimentEvaluations) {
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

  const rows = Array.from(rowLabels).sort((a, b) => plotSortCollator.compare(a, b));
  const cols = Array.from(colLabels).sort((a, b) => plotSortCollator.compare(a, b));
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

export function buildTpFpFnTabMap({
  plotGroups,
  experimentEvaluations,
  labelFields,
  evalTabState,
  confusionTabsBy,
  getEvaluationEffectiveValue,
  displayPlotGroupFieldName,
  shortenLabels = false,
}) {
  const tabMap = new Map();
  const normalizedExperimentEvaluations = normalizeTpFpFnLikeEvaluations(experimentEvaluations);

  const groupEntries = plotGroups
    .map((group, index) => ({
      key: `group|#|${group.groupId}`,
      label: getGroupLabelForFields(
        group,
        labelFields,
        `group ${index + 1}`,
        displayPlotGroupFieldName
      ),
      evaluations: normalizeTpFpFnLikeEvaluations(group.evaluations),
    }))
    .filter((entry) => entry.evaluations.length > 0);

  if (confusionTabsBy === "metric_field") {
    for (const evaluation of normalizedExperimentEvaluations) {
      const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
      const fieldLabel = rawField || "(missing metric.field)";
      if (!tabMap.has(fieldLabel)) {
        tabMap.set(fieldLabel, {
          label: getPlotDisplayLabel(fieldLabel, { shortenLabels }),
          plots: [],
        });
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
        tab.plots.push({
          label: groupEntry.label,
          fieldLabel: fieldKey,
          evaluations: evaluationsForFieldAndGroup,
        });
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
      .sort(([a], [b]) => plotSortCollator.compare(a, b))
      .map(([fieldLabel, evaluations]) => ({
        label: fieldLabel,
        fieldLabel,
        evaluations,
      }));
    tabMap.set(groupEntry.key, { label: groupEntry.label, plots });
  }

  return tabMap;
}

export function buildTpFpFnCellSummary(row, col, stats, totalEvaluations, evaluationLabels, precision) {
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
