/**
 * Shared table sorting, truncation, and sticky-offset helpers for the eval dashboard.
 */

import { normalizeSortConfig } from "../utils/sort.js";

/**
 * Return the default sort direction for one dashboard table column.
 *
 * @param {string} column - The column identifier being sorted.
 * @param {Set<string>} sortableControlColumns - Control columns that default to descending order.
 * @returns {"asc" | "desc"} The column's default sort direction.
 */
export function getDefaultSortDirection(column, sortableControlColumns) {
  return sortableControlColumns.has(column) ? "desc" : "asc";
}

/**
 * Format one sort column into the human-readable label shown in status text.
 *
 * @param {string} column - The canonical column identifier.
 * @param {(column: string) => string} displayColumnName - Formatter for data columns.
 * @returns {string} A display label for the column.
 */
export function getSortColumnLabel(column, displayColumnName) {
  if (column === "group_size") {
	return "group size";
  }
  if (column === "select") {
	return "selected";
  }
  if (column === "expand") {
	return "expanded";
  }
  return displayColumnName(column);
}

/**
 * Format the active sort configuration for display in the table status area.
 *
 * @param {Array<{column: string, direction: string}> | object | null} sortConfig - The current sort configuration.
 * @param {(column: string) => string} displayColumnName - Formatter for data columns.
 * @returns {string} Human-readable sort status text.
 */
export function formatSortLabel(sortConfig, displayColumnName) {
  const activeSorts = normalizeSortConfig(sortConfig);
  if (!activeSorts.length) {
	return "(none)";
  }
  return activeSorts.map((clause, index) => (
	`${getSortColumnLabel(clause.column, displayColumnName)} ${clause.direction === "desc" ? "↓" : "↑"}` +
	(activeSorts.length > 1 ? ` (${index + 1})` : "")
  )).join(", ");
}

/**
 * Compute the next sort direction in the dashboard's three-state cycle.
 *
 * @param {"asc" | "desc" | null} currentDirection - The current direction for the column.
 * @param {string} column - The column being toggled.
 * @param {Set<string>} sortableControlColumns - Control columns that default to descending order.
 * @returns {"asc" | "desc" | null} The next direction, or null when sorting should be cleared.
 */
export function getNextSortDirection(currentDirection, column, sortableControlColumns) {
  const defaultDirection = getDefaultSortDirection(column, sortableControlColumns);
  if (!currentDirection) {
	return defaultDirection;
  }
  return currentDirection === defaultDirection
	? defaultDirection === "asc" ? "desc" : "asc"
	: null;
}

/**
 * Compute the next normalized sort configuration after toggling one column.
 *
 * @param {Array<{column: string, direction: string}> | object | null} currentSort - The current sort configuration.
 * @param {string} column - The column being toggled.
 * @param {{append?: boolean, sortableControlColumns: Set<string>}} options - Sort-toggle options.
 * @returns {Array<{column: string, direction: string}>} The next normalized sort configuration.
 */
export function getNextSortConfig(currentSort, column, { append = false, sortableControlColumns } = {}) {
  const currentSorts = normalizeSortConfig(currentSort);
  const currentIndex = currentSorts.findIndex((clause) => clause.column === column);
  const currentDirection = currentIndex === -1 ? null : currentSorts[currentIndex].direction;
  const nextDirection = getNextSortDirection(currentDirection, column, sortableControlColumns);
  if (!append) {
	return nextDirection ? [{ column, direction: nextDirection }] : [];
  }
  if (currentIndex === -1) {
	return nextDirection ? [...currentSorts, { column, direction: nextDirection }] : currentSorts;
  }
  if (!nextDirection) {
	return currentSorts.filter((clause) => clause.column !== column);
  }
  const nextSorts = [...currentSorts];
  nextSorts[currentIndex] = { column, direction: nextDirection };
  return nextSorts;
}

/**
 * Return the current `aria-sort` value for one table header cell.
 *
 * @param {Array<{column: string, direction: string}> | object | null} sortConfig - The active sort configuration.
 * @param {string} column - The column whose aria state should be derived.
 * @returns {"none" | "ascending" | "descending"} The aria-sort value.
 */
export function getAriaSort(sortConfig, column) {
  const primarySort = normalizeSortConfig(sortConfig)[0];
  if (!primarySort || primarySort.column !== column) {
	return "none";
  }
  return primarySort.direction === "desc" ? "descending" : "ascending";
}

/**
 * Return the 1-based priority of one column within the current sort config.
 *
 * @param {Array<{column: string, direction: string}> | object | null} sortConfig - The active sort configuration.
 * @param {string} column - The column to look up.
 * @returns {number} The 1-based sort priority, or 0 when the column is inactive.
 */
export function getSortPriority(sortConfig, column) {
  const priority = normalizeSortConfig(sortConfig).findIndex((clause) => clause.column === column);
  return priority === -1 ? 0 : priority + 1;
}

/**
 * Create one reusable header sort button for prediction or evaluation tables.
 *
 * @param {object} options - Sort-button options.
 * @param {Document} [options.documentLike=globalThis.document] - The document used to create DOM nodes.
 * @param {string} options.label - The displayed button label.
 * @param {string} options.column - The canonical column identifier.
 * @param {Array<{column: string, direction: string}> | object | null} options.sortConfig - The active sort configuration.
 * @param {(event: MouseEvent) => void} options.onToggle - Toggle callback invoked on click.
 * @param {Set<string>} options.sortableControlColumns - Control columns that default to descending order.
 * @returns {HTMLButtonElement} The configured sort button.
 */
export function createSortButton({
  documentLike = globalThis.document,
  label,
  column,
  sortConfig,
  onToggle,
  sortableControlColumns,
}) {
  const normalizedSorts = normalizeSortConfig(sortConfig);
  const priority = getSortPriority(normalizedSorts, column);
  const isActive = priority > 0;
  const activeClause = isActive ? normalizedSorts[priority - 1] : null;
  const button = documentLike.createElement("button");
  button.type = "button";
  button.className = "header-sort-button" + (isActive ? " active" : "");
  const totalActiveSorts = normalizedSorts.length;
  const nextSingleSort = getNextSortConfig(normalizedSorts, column, { sortableControlColumns });
  const singleActionText = nextSingleSort.length
	? `sort only by ${label} ${nextSingleSort[0].direction === "asc" ? "ascending" : "descending"}`
	: `clear sorting for ${label}`;
  button.title = `Click: ${singleActionText}. Shift-click: add, toggle, or remove ${label} in multi-column sorting.`;
  button.setAttribute(
	"aria-label",
	isActive
	  ? `${label}, sort priority ${priority}, ${activeClause.direction === "asc" ? "ascending" : "descending"}`
	  : `${label}, not sorted`
  );
  button.addEventListener("click", (event) => {
	event.stopPropagation();
	onToggle(event);
  });

  const labelSpan = documentLike.createElement("span");
  labelSpan.textContent = label;
  const indicator = documentLike.createElement("span");
  indicator.className = "header-sort-indicator";
  indicator.textContent = !isActive
	? "↕"
	: `${activeClause.direction === "asc" ? "▲" : "▼"}${totalActiveSorts > 1 ? priority : ""}`;
  indicator.setAttribute("aria-hidden", "true");

  button.appendChild(labelSpan);
  button.appendChild(indicator);
  return button;
}

/**
 * Create one table cell with the dashboard's shared truncation class behavior.
 *
 * @param {object} options - Cell creation options.
 * @param {Document} [options.documentLike=globalThis.document] - The document used to create DOM nodes.
 * @param {string} options.content - Cell text content.
 * @param {string} [options.columnKey=""] - Column identifier used for truncation matching.
 * @param {Set<string> | null} [options.truncateEnabledColumns=null] - Enabled truncation columns.
 * @returns {HTMLTableCellElement} The created table cell.
 */
export function createTruncatingCell({
  documentLike = globalThis.document,
  content,
  columnKey = "",
  truncateEnabledColumns = null,
}) {
  const td = documentLike.createElement("td");
  td.textContent = content;
  if (columnKey && truncateEnabledColumns?.has(columnKey)) {
	td.classList.add("truncate-enabled");
  }
  return td;
}

/**
 * Recompute sticky control-column offsets after a table render or resize.
 *
 * @param {HTMLTableElement | null} tableElement - The table whose sticky offsets should be updated.
 * @returns {void}
 */
export function updateStickyControlColumnOffsets(tableElement) {
  if (!tableElement) {
	return;
  }
  const firstHeaderRow = tableElement.tHead?.rows?.[0];
  if (!firstHeaderRow || firstHeaderRow.cells.length < 3) {
	tableElement.style.setProperty("--sticky-col-1-left", "0px");
	tableElement.style.setProperty("--sticky-col-2-left", "0px");
	tableElement.style.setProperty("--sticky-col-3-left", "0px");
	tableElement.style.setProperty("--sticky-header-row-1-height", "0px");
	return;
  }
  const widths = Array.from(firstHeaderRow.cells)
	.slice(0, 3)
	.map((cell) => Math.ceil(cell.getBoundingClientRect().width));
  const topHeaderCell =
	Array.from(firstHeaderRow.cells).find((cell) => cell.rowSpan === 1) || firstHeaderRow.cells[0];
  tableElement.style.setProperty("--sticky-col-1-left", "0px");
  tableElement.style.setProperty("--sticky-col-2-left", `${widths[0]}px`);
  tableElement.style.setProperty("--sticky-col-3-left", `${widths[0] + widths[1]}px`);
  tableElement.style.setProperty(
	"--sticky-header-row-1-height",
	`${Math.ceil(topHeaderCell.getBoundingClientRect().height)}px`
  );
}

