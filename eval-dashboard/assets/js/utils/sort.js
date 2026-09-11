/**
 * Sorting helpers shared by eval dashboard table and plot views.
 */

import { normalizeValue } from "./values.js";

const sortCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

/**
 * Normalize a sort configuration into a deduplicated list of valid sort clauses.
 *
 * @param {unknown} sortConfig - Raw single- or multi-column sort configuration.
 * @param {Iterable<string> | null} [validColumns=null] - Optional allow-list of sortable columns.
 * @returns {Array<{column: string, direction: "asc" | "desc"}>} The normalized sort clauses.
 */
export function normalizeSortConfig(sortConfig, validColumns = null) {
  const sourceClauses = Array.isArray(sortConfig)
    ? sortConfig
    : sortConfig?.column
      ? [sortConfig]
      : [];
  const allowedColumns = validColumns ? new Set(validColumns) : null;
  const normalizedClauses = [];
  const seenColumns = new Set();
  for (const clause of sourceClauses) {
    if (!clause || typeof clause.column !== "string") {
      continue;
    }
    if (clause.direction !== "asc" && clause.direction !== "desc") {
      continue;
    }
    if (allowedColumns && !allowedColumns.has(clause.column)) {
      continue;
    }
    if (seenColumns.has(clause.column)) {
      continue;
    }
    seenColumns.add(clause.column);
    normalizedClauses.push({ column: clause.column, direction: clause.direction });
  }
  return normalizedClauses;
}

/**
 * Parse a normalized sortable value as a finite number when possible.
 *
 * @param {unknown} value - The value to parse.
 * @returns {number | null} The parsed number, or `null` if the value is not numeric.
 */
export function parseSortableNumber(value) {
  const normalized = normalizeValue(value).trim();
  if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(normalized)) {
    return null;
  }
  const numericValue = Number(normalized);
  return Number.isFinite(numericValue) ? numericValue : null;
}

/**
 * Compare two values using the dashboard's blank-last, numeric-first ordering rules.
 *
 * @param {unknown} a - The left-hand value.
 * @param {unknown} b - The right-hand value.
 * @returns {number} A standard comparator result.
 */
export function compareSortableValues(a, b) {
  const normalizedA = normalizeValue(a).trim();
  const normalizedB = normalizeValue(b).trim();
  const isBlankA = normalizedA === "";
  const isBlankB = normalizedB === "";
  if (isBlankA || isBlankB) {
    if (isBlankA && isBlankB) {
      return 0;
    }
    return isBlankA ? 1 : -1;
  }
  const numericA = parseSortableNumber(normalizedA);
  const numericB = parseSortableNumber(normalizedB);
  if (numericA !== null && numericB !== null) {
    return numericA - numericB;
  }
  return sortCollator.compare(normalizedA, normalizedB);
}

/**
 * Return a stably sorted copy of the provided items.
 *
 * @template T
 * @param {T[]} items - The items to sort.
 * @param {unknown} sortConfig - Raw sort configuration.
 * @param {(item: T, column: string) => unknown} valueGetter - Callback returning the value for a given item/column.
 * @returns {T[]} A new array ordered according to the normalized sort configuration.
 */
export function sortItems(items, sortConfig, valueGetter) {
  const normalizedSorts = normalizeSortConfig(sortConfig);
  if (!normalizedSorts.length) {
    return [...items];
  }
  return items
    .map((item, index) => ({ item, index }))
    .sort((left, right) => {
      for (const clause of normalizedSorts) {
        const comparison = compareSortableValues(
          valueGetter(left.item, clause.column),
          valueGetter(right.item, clause.column)
        );
        if (comparison !== 0) {
          return comparison * (clause.direction === "desc" ? -1 : 1);
        }
      }
      return left.index - right.index;
    })
    .map(({ item }) => item);
}
