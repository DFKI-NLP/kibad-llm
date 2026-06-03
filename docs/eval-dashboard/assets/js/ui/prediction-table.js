/**
 * Prediction-table helpers and renderer for the eval dashboard.
 */

import { createGroupByToggleControl } from "./controls.js";
import {
  buildSelectionState,
  createSelectHeaderCell,
  createSortButton,
  createStaticControlHeaderCell,
  createTruncatingCell,
  getAriaSort,
} from "./table-shared.js";

/**
 * Build the plain row model for one grouped prediction row.
 *
 * @param {object} options - Prediction-group row inputs.
 * @param {{groupId: string, predictions?: Array<object>}} options.group - Prediction group.
 * @param {Iterable<string>} options.orderedColumns - Ordered prediction columns.
 * @param {boolean} [options.isExpanded=false] - Whether the group is expanded.
 * @param {boolean} [options.isSelected=false] - Whether the group is selected.
 * @param {(group: object, column: string) => string} options.getGroupValueDisplay - Group-value formatter.
 * @returns {{groupId: string, groupSize: number, isExpanded: boolean, isSelected: boolean, valueCells: Array<{column: string, content: string}>}} Plain row model.
 */
export function buildPredictionGroupRowModel({
  group,
  orderedColumns,
  isExpanded = false,
  isSelected = false,
  getGroupValueDisplay,
}) {
  return {
    groupId: group.groupId,
    groupSize: Array.isArray(group.predictions) ? group.predictions.length : 0,
    isExpanded,
    isSelected,
    valueCells: Array.from(orderedColumns || []).map((column) => ({
      column,
      content: getGroupValueDisplay(group, column),
    })),
  };
}

/**
 * Build the plain row model for one expanded prediction-member row.
 *
 * @param {object} options - Prediction-member row inputs.
 * @param {{predictionFlat?: object}} options.member - Prediction member entry.
 * @param {Iterable<string>} options.orderedColumns - Ordered prediction columns.
 * @param {(predictionFlat: object, column: string) => string} options.getPredictionEffectiveValue - Effective-value formatter.
 * @returns {{groupSizeLabel: string, valueCells: Array<{column: string, content: string}>}} Plain member-row model.
 */
export function buildPredictionMemberRowModel({
  member,
  orderedColumns,
  getPredictionEffectiveValue,
}) {
  return {
    groupSizeLabel: "member",
    valueCells: Array.from(orderedColumns || []).map((column) => ({
      column,
      content: getPredictionEffectiveValue(member.predictionFlat, column),
    })),
  };
}

/**
 * Append one ordered set of truncating value cells to the provided row element.
 *
 * @param {object} options - Row-cell render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLTableRowElement} options.rowElement - Row receiving the cells.
 * @param {Array<{column: string, content: string}>} options.valueCells - Plain value-cell models.
 * @param {Set<string>} options.truncateEnabledColumns - Enabled truncation columns.
 * @returns {void}
 */
function appendPredictionValueCells({
  documentLike,
  rowElement,
  valueCells,
  truncateEnabledColumns,
}) {
  for (const valueCell of valueCells || []) {
    rowElement.appendChild(
      createTruncatingCell({
        documentLike,
        content: valueCell.content,
        columnKey: valueCell.column,
        truncateEnabledColumns,
      })
    );
  }
}

/**
 * Render the prediction-table header rows.
 *
 * @param {object} options - Header render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {Array<{label: string, columns: string[]}>} options.predictionSections - Column sections.
 * @param {Iterable<string>} options.orderedPredictionColumns - Ordered prediction columns.
 * @param {Array<{column: string, direction: string}> | object | null} options.predictionSort - Active sort config.
 * @param {Set<string>} options.truncateEnabledColumns - Enabled truncation columns.
 * @param {Iterable<string>} options.groupByFields - Active group-by fields.
 * @param {(column: string) => string} options.displayColumnName - Header-label formatter.
 * @param {(column: string, event: Event) => void} options.onSortToggle - Sort toggle callback.
 * @param {(column: string, checked: boolean) => void} options.onToggleGroupByColumn - Group-by toggle callback.
 * @param {(checked: boolean, displayedGroupIds: string[]) => void} options.onSelectAllDisplayed - Select-all callback.
 * @param {{displayedGroupIds: string[], selectedCount: number, allSelected: boolean, someSelected: boolean}} options.selectionState - Shared selection state.
 * @param {Set<string>} options.sortableControlColumns - Control columns that default to descending order.
 * @returns {HTMLTableSectionElement} The rendered table header.
 */
function renderPredictionTableHead({
  documentLike,
  predictionSections,
  orderedPredictionColumns,
  predictionSort,
  truncateEnabledColumns,
  groupByFields,
  displayColumnName,
  onSortToggle,
  onToggleGroupByColumn,
  onSelectAllDisplayed,
  selectionState,
  sortableControlColumns,
}) {
  const groupByFieldSet = new Set(groupByFields || []);
  const thead = documentLike.createElement("thead");
  const sectionRow = documentLike.createElement("tr");
  sectionRow.appendChild(
    createStaticControlHeaderCell({
      documentLike,
      label: "expand",
      column: "expand",
      sortConfig: predictionSort,
      onToggle: (event) => onSortToggle("expand", event),
      sortableControlColumns,
    })
  );
  sectionRow.appendChild(
    createSelectHeaderCell({
      documentLike,
      sortConfig: predictionSort,
      onToggle: (event) => onSortToggle("select", event),
      selectionState,
      onSelectAllToggle: (checked) => onSelectAllDisplayed(checked, selectionState.displayedGroupIds),
      sortableControlColumns,
      checkboxTitle: "Select or deselect all displayed groups",
      checkboxAriaLabel: "Select or deselect all displayed prediction groups",
    })
  );
  sectionRow.appendChild(
    createStaticControlHeaderCell({
      documentLike,
      label: "#",
      column: "group_size",
      sortConfig: predictionSort,
      onToggle: (event) => onSortToggle("group_size", event),
      sortableControlColumns,
    })
  );

  for (const section of predictionSections || []) {
    const th = documentLike.createElement("th");
    th.className = "section-header";
    th.colSpan = section.columns.length;
    th.textContent = section.label;
    sectionRow.appendChild(th);
  }
  thead.appendChild(sectionRow);

  const columnRow = documentLike.createElement("tr");
  for (const column of orderedPredictionColumns || []) {
    const th = documentLike.createElement("th");
    th.setAttribute("aria-sort", getAriaSort(predictionSort, column));
    if (truncateEnabledColumns?.has(column)) {
      th.classList.add("truncate-enabled");
    }
    const headerLabel = displayColumnName(column);
    const headerControl = documentLike.createElement("div");
    headerControl.className = "header-column-control";
    headerControl.appendChild(
      createSortButton({
        documentLike,
        label: headerLabel,
        column,
        sortConfig: predictionSort,
        onToggle: (event) => onSortToggle(column, event),
        sortableControlColumns,
      })
    );
    headerControl.appendChild(
      createGroupByToggleControl({
        documentLike,
        checked: groupByFieldSet.has(column),
        ariaLabel: `Group by ${headerLabel}`,
        onToggle: (checked) => onToggleGroupByColumn(column, checked),
      })
    );
    th.appendChild(headerControl);
    columnRow.appendChild(th);
  }
  thead.appendChild(columnRow);
  return thead;
}

/**
 * Render the prediction table body rows from grouped and member-row models.
 *
 * @param {object} options - Body render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {Iterable<object>} options.displayedGroups - Displayed prediction groups.
 * @param {Iterable<string>} options.orderedPredictionColumns - Ordered prediction columns.
 * @param {Set<string>} options.truncateEnabledColumns - Enabled truncation columns.
 * @param {Set<string>} options.selectedGroupIds - Selected prediction-group ids.
 * @param {Set<string>} options.expandedGroupIds - Expanded prediction-group ids.
 * @param {(groupId: string) => void} options.onToggleGroupExpansion - Expand-toggle callback.
 * @param {(groupId: string, checked: boolean) => void} options.onToggleGroupSelection - Group-selection callback.
 * @param {(group: object, column: string) => string} options.getGroupValueDisplay - Group-value formatter.
 * @param {(predictions: Array<object>) => Array<object>} options.getSortedPredictionMembers - Prediction-member sorter.
 * @param {(predictionFlat: object, column: string) => string} options.getPredictionEffectiveValue - Effective-value formatter.
 * @returns {HTMLTableSectionElement} The rendered table body.
 */
function renderPredictionTableBody({
  documentLike,
  displayedGroups,
  orderedPredictionColumns,
  truncateEnabledColumns,
  selectedGroupIds,
  expandedGroupIds,
  onToggleGroupExpansion,
  onToggleGroupSelection,
  getGroupValueDisplay,
  getSortedPredictionMembers,
  getPredictionEffectiveValue,
}) {
  const tbody = documentLike.createElement("tbody");
  for (const group of displayedGroups || []) {
    const groupModel = buildPredictionGroupRowModel({
      group,
      orderedColumns: orderedPredictionColumns,
      isExpanded: expandedGroupIds.has(group.groupId),
      isSelected: selectedGroupIds.has(group.groupId),
      getGroupValueDisplay,
    });
    const tr = documentLike.createElement("tr");

    const expandTd = documentLike.createElement("td");
    const expandButton = documentLike.createElement("button");
    expandButton.type = "button";
    expandButton.className = "expand-button";
    expandButton.textContent = groupModel.isExpanded ? "-" : "+";
    expandButton.title = groupModel.isExpanded ? "Collapse group members" : "Expand group members";
    expandButton.addEventListener("click", () => onToggleGroupExpansion(group.groupId));
    expandTd.appendChild(expandButton);
    tr.appendChild(expandTd);

    const selectTd = documentLike.createElement("td");
    const checkbox = documentLike.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = groupModel.isSelected;
    checkbox.addEventListener("change", () => onToggleGroupSelection(group.groupId, checkbox.checked));
    selectTd.appendChild(checkbox);
    tr.appendChild(selectTd);

    tr.appendChild(
      createTruncatingCell({
        documentLike,
        content: String(groupModel.groupSize),
      })
    );
    appendPredictionValueCells({
      documentLike,
      rowElement: tr,
      valueCells: groupModel.valueCells,
      truncateEnabledColumns,
    });
    tbody.appendChild(tr);

    if (!groupModel.isExpanded) {
      continue;
    }

    const sortedMembers = getSortedPredictionMembers(group.predictions || []);
    for (const member of sortedMembers) {
      const memberModel = buildPredictionMemberRowModel({
        member,
        orderedColumns: orderedPredictionColumns,
        getPredictionEffectiveValue,
      });
      const memberRow = documentLike.createElement("tr");
      memberRow.className = "member-row";
      memberRow.appendChild(createTruncatingCell({ documentLike, content: "" }));
      memberRow.appendChild(createTruncatingCell({ documentLike, content: "" }));
      memberRow.appendChild(
        createTruncatingCell({
          documentLike,
          content: memberModel.groupSizeLabel,
        })
      );
      appendPredictionValueCells({
        documentLike,
        rowElement: memberRow,
        valueCells: memberModel.valueCells,
        truncateEnabledColumns,
      });
      tbody.appendChild(memberRow);
    }
  }
  return tbody;
}

/**
 * Render the full prediction table from selector-derived prediction groups.
 *
 * @param {object} options - Prediction-table render inputs.
 * @param {Document} [options.documentLike=globalThis.document] - Document-like element factory.
 * @param {HTMLTableElement | null} options.tableElement - Target table element.
 * @param {Array<{label: string, columns: string[]}>} options.predictionSections - Prediction column sections.
 * @param {Iterable<string>} options.orderedPredictionColumns - Ordered prediction columns.
 * @param {Iterable<object>} options.displayedGroups - Displayed prediction groups.
 * @param {Array<{column: string, direction: string}> | object | null} options.predictionSort - Active sort config.
 * @param {Set<string>} options.truncateEnabledColumns - Enabled truncation columns.
 * @param {Iterable<string>} options.groupByFields - Active group-by fields.
 * @param {Set<string>} options.selectedGroupIds - Selected prediction-group ids.
 * @param {Set<string>} options.expandedGroupIds - Expanded prediction-group ids.
 * @param {(column: string) => string} options.displayColumnName - Header-label formatter.
 * @param {(column: string, event: Event) => void} options.onSortToggle - Sort toggle callback.
 * @param {(column: string, checked: boolean) => void} options.onToggleGroupByColumn - Group-by toggle callback.
 * @param {(groupId: string) => void} options.onToggleGroupExpansion - Expand-toggle callback.
 * @param {(groupId: string, checked: boolean) => void} options.onToggleGroupSelection - Group-selection callback.
 * @param {(checked: boolean, displayedGroupIds: string[]) => void} options.onSelectAllDisplayed - Select-all callback.
 * @param {(group: object, column: string) => string} options.getGroupValueDisplay - Group-value formatter.
 * @param {(predictions: Array<object>) => Array<object>} options.getSortedPredictionMembers - Prediction-member sorter.
 * @param {(predictionFlat: object, column: string) => string} options.getPredictionEffectiveValue - Effective-value formatter.
 * @param {Set<string>} options.sortableControlColumns - Control columns that default to descending order.
 * @returns {{displayedGroupIds: string[], selectedCount: number, allSelected: boolean, someSelected: boolean}} The rendered selection state.
 */
export function renderPredictionTable({
  documentLike = globalThis.document,
  tableElement,
  predictionSections,
  orderedPredictionColumns,
  displayedGroups,
  predictionSort,
  truncateEnabledColumns,
  groupByFields,
  selectedGroupIds,
  expandedGroupIds,
  displayColumnName,
  onSortToggle,
  onToggleGroupByColumn,
  onToggleGroupExpansion,
  onToggleGroupSelection,
  onSelectAllDisplayed,
  getGroupValueDisplay,
  getSortedPredictionMembers,
  getPredictionEffectiveValue,
  sortableControlColumns,
}) {
  const selectionState = buildSelectionState(
    Array.from(displayedGroups || []).map((group) => group.groupId),
    selectedGroupIds
  );
  if (!tableElement) {
    return selectionState;
  }
  tableElement.innerHTML = "";
  tableElement.appendChild(
    renderPredictionTableHead({
      documentLike,
      predictionSections,
      orderedPredictionColumns,
      predictionSort,
      truncateEnabledColumns,
      groupByFields,
      displayColumnName,
      onSortToggle,
      onToggleGroupByColumn,
      onSelectAllDisplayed,
      selectionState,
      sortableControlColumns,
    })
  );
  tableElement.appendChild(
    renderPredictionTableBody({
      documentLike,
      displayedGroups,
      orderedPredictionColumns,
      truncateEnabledColumns,
      selectedGroupIds,
      expandedGroupIds,
      onToggleGroupExpansion,
      onToggleGroupSelection,
      getGroupValueDisplay,
      getSortedPredictionMembers,
      getPredictionEffectiveValue,
    })
  );
  return selectionState;
}
