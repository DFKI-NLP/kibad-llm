/**
 * Shared DOM-free plot helpers for the eval dashboard.
 */

import { splitLabelByLastDot } from "../utils/text.js";
import { normalizeValue } from "../utils/values.js";

export const TP_FP_FN_KEYS = ["tp", "fp", "fn"];
export const plotSortCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

/**
 * Resolves the stable source run directory for a metric collection evaluation.
 *
 * @param {object} evaluation - Evaluation record.
 * @returns {string} Normalized source run directory.
 */
export function getMetricCollectionSourceRunDir(evaluation) {
  return normalizeValue(evaluation?.sourceRunDir ?? evaluation?.runDir).trim();
}

/**
 * Check whether a value is a plain object record.
 *
 * @param {*} value - Candidate record.
 * @returns {boolean} Whether the value is a non-array object.
 */
export function isMetricDataRecord(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

/**
 * Resolves the non-enumerable prepared-data container for a metric evaluation.
 *
 * Collection views keep the raw dashboard evaluation on `.evaluation`; caching
 * on that source record lets rebuilt views reuse the same prepared data. Direct
 * aggregation inputs fall back to the object they received.
 *
 * @param {object} evaluation - Collection view or direct evaluation.
 * @returns {object} Mutable prepared-data container.
 * @throws {Error} If the input cannot own prepared data.
 */
export function getMetricPreparedDataContainer(evaluation) {
  const cacheTarget = evaluation?.evaluation && typeof evaluation.evaluation === "object"
    ? evaluation.evaluation
    : evaluation;
  if (!cacheTarget || typeof cacheTarget !== "object") {
    throw new Error("Metric preparation cache target must be an object.");
  }
  if (!cacheTarget.dataPrepared || typeof cacheTarget.dataPrepared !== "object") {
    Object.defineProperty(cacheTarget, "dataPrepared", {
      value: Object.create(null),
      enumerable: false,
      configurable: true,
      writable: true,
    });
  } else if (Object.getPrototypeOf(cacheTarget.dataPrepared) !== null) {
    const preparedData = Object.assign(Object.create(null), cacheTarget.dataPrepared);
    Object.defineProperty(cacheTarget, "dataPrepared", {
      value: preparedData,
      enumerable: false,
      configurable: true,
      writable: true,
    });
  }
  return cacheTarget.dataPrepared;
}

/**
 * Build a collection-view wrapper for one field-based metric evaluation.
 *
 * Collection metrics expose their field map by reference. Single-field metrics
 * are wrapped as one-field collections and must define a non-empty metric.field.
 *
 * @param {object} evaluation - Evaluation record to wrap.
 * @param {object} options - Collection type names, metric label, and field resolver.
 * @returns {object} Collection-view record.
 * @throws {Error} If the evaluation shape violates the metric contract.
 */
export function getMetricCollectionView(
  evaluation,
  { collectionType, singularType, metricLabel, evalTabState, getEvaluationEffectiveValue }
) {
  if (!evaluation || typeof evaluation !== "object") {
    throw new Error(`${metricLabel} evaluation must be an object.`);
  }

  const metricType = normalizeValue(evaluation?.jobReturnValue?.type).trim();
  const sourceRunDir = getMetricCollectionSourceRunDir(evaluation);
  if (metricType === collectionType) {
    const fieldEntries = evaluation.data;
    if (!isMetricDataRecord(fieldEntries)) {
      throw new Error(`${collectionType} data must be an object mapping metric fields to metric data.`);
    }

    const fields = new Map();
    for (const [rawField, fieldEntry] of Object.entries(fieldEntries)) {
      const fieldLabel = normalizeValue(rawField).trim();
      if (!fieldLabel) {
        throw new Error(`${collectionType} data contains an empty metric field name.`);
      }
      if (fields.has(fieldLabel)) {
        throw new Error(`${collectionType} data contains duplicate metric field ${JSON.stringify(fieldLabel)} after normalization.`);
      }
      if (!isMetricDataRecord(fieldEntry)) {
        throw new Error(`${collectionType} field ${JSON.stringify(fieldLabel)} must contain object metric data.`);
      }
      fields.set(fieldLabel, fieldEntry);
    }
    if (fields.size === 0) {
      throw new Error(`${collectionType} data must contain at least one metric field.`);
    }

    return {
      evaluation,
      runDir: normalizeValue(evaluation?.runDir) || sourceRunDir,
      sourceRunDir,
      fields,
    };
  }

  if (metricType === singularType) {
    const rawField = getEvaluationEffectiveValue
      ? getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState)
      : evaluation?.overrides?.["metric.field"];
    const fieldLabel = normalizeValue(rawField).trim();
    if (!fieldLabel) {
      throw new Error(`${singularType} evaluation must define a non-empty metric.field.`);
    }
    if (!isMetricDataRecord(evaluation.data)) {
      throw new Error(`${singularType} data must be an object.`);
    }
    return {
      evaluation,
      runDir: normalizeValue(evaluation?.runDir) || sourceRunDir,
      sourceRunDir,
      fields: new Map([[fieldLabel, evaluation.data]]),
    };
  }

  throw new Error(`${metricLabel} plot received unsupported metric type: ${metricType || "(missing)"}.`);
}

/**
 * Formats a plot label, optionally shortening dotted paths to their suffix.
 *
 * @param {*} label - Raw label value.
 * @param {object} [options] - Display options.
 * @returns {string} Normalized label text.
 */
export function getPlotDisplayLabel(label, { shortenLabels = false } = {}) {
  const text = normalizeValue(label);
  return shortenLabels ? splitLabelByLastDot(text) : text;
}

/**
 * Selects a deterministic bar color from the dashboard palette.
 *
 * @param {number} index - Zero-based series index.
 * @returns {string} Hex color value.
 */
export function getBarColor(index) {
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

/**
 * Applies shared visual styling to an SVG error-bar line segment.
 *
 * @param {SVGLineElement} line - Line element to style.
 * @returns {void}
 */
export function styleErrorBarSegment(line) {
  line.setAttribute("stroke", "currentColor");
  line.setAttribute("stroke-opacity", "0.78");
}

/**
 * Expands an SVG viewport so all generated plot content is visible.
 *
 * @param {SVGSVGElement} svg - SVG element to resize.
 * @param {SVGGElement} contentGroup - Group whose bounding box is measured.
 * @param {number} minWidth - Minimum SVG width.
 * @param {number} minHeight - Minimum SVG height.
 * @returns {boolean} True when fitting succeeded.
 */
export function fitSvgToContents(svg, contentGroup, minWidth, minHeight) {
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

/**
 * Schedules repeated SVG fitting attempts after layout and font loading.
 *
 * @param {object} options - Fitting dependencies and dimensions.
 * @returns {void}
 */
export function scheduleAdaptiveSvgFit({
  documentLike = globalThis.document,
  requestAnimationFrameLike = globalThis.requestAnimationFrame,
  svg,
  contentGroup,
  minWidth,
  minHeight,
}) {
  let attempts = 4;
  const requestFrame = requestAnimationFrameLike || ((callback) => callback());
  const runFit = () => {
    const fitted = fitSvgToContents(svg, contentGroup, minWidth, minHeight);
    if (!fitted && attempts > 0) {
      attempts -= 1;
      requestFrame(runFit);
    }
  };

  requestFrame(runFit);
  if (documentLike?.fonts?.ready) {
    documentLike.fonts.ready
      .then(() => {
        requestFrame(runFit);
      })
      .catch(() => {});
  }
}

/**
 * Builds a shared legend model for grouped bar plot entries.
 *
 * @param {Array<object>} entries - Plot entries containing grouped points.
 * @returns {object} Series order, display labels, colors, and legend items.
 */
export function buildGroupedLegendModel(entries) {
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

/**
 * Filters a legend model down to the series present in a point collection.
 *
 * @param {Array<object>} points - Points rendered in a plot.
 * @param {?object} legendModel - Shared legend model.
 * @returns {Array<object>} Legend items used by the points.
 */
export function getLegendItemsForPoints(points, legendModel) {
  if (!legendModel) {
    return [];
  }
  const seriesInPoints = new Set(points.map((point) => point.series));
  return legendModel.items.filter((item) => seriesInPoints.has(item.series));
}

/**
 * Finds grouping fields whose values differ across groups.
 *
 * @param {Array<object>} groups - Plot groups with value maps.
 * @param {Array<string>} fields - Candidate field names.
 * @returns {Array<string>} Fields with more than one normalized value.
 */
export function getVaryingFields(groups, fields) {
  if (!fields.length || groups.length <= 1) {
    return [];
  }
  return fields.filter((field) => {
    const values = new Set(groups.map((group) => normalizeValue(group.values?.[field])));
    return values.size > 1;
  });
}

/**
 * Builds a readable label from selected group fields.
 *
 * @param {object} group - Plot group containing values.
 * @param {Array<string>} labelFields - Field names to include.
 * @param {string} fallback - Label used when no fields are selected.
 * @param {Function} [fieldNameFormatter] - Formatter for field names.
 * @returns {string} Group label text.
 */
export function getGroupLabelForFields(
  group,
  labelFields,
  fallback,
  fieldNameFormatter = (field) => field
) {
  if (labelFields.length === 0) {
    return fallback;
  }
  return labelFields
    .map((field) => `${fieldNameFormatter(field)}=${normalizeValue(group.values[field])}`)
    .join(" | ");
}
