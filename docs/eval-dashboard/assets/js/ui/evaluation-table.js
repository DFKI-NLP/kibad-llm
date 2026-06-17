/**
 * Evaluation-table helpers and renderer for the eval dashboard.
 */

import { normalizeValue } from "../utils/values.js";
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
 * Split ordered evaluation columns into the table header sections rendered by the
 * evaluation table.
 *
 * @param {Iterable<string>} evalColumns - Evaluation columns to organize.
 * @param {object} options - Section-builder callbacks.
 * @param {(column: string) => boolean} options.isJobReturnValueColumn - Job-return-value predicate.
 * @returns {Array<{label: string, columns: string[]}>} Ordered non-empty section models.
 */
export function buildEvaluationColumnSections(evalColumns, { isJobReturnValueColumn }) {
  const resolvedColumns = Array.from(evalColumns || []);
  const overrides = resolvedColumns.filter((column) => !isJobReturnValueColumn(column)).sort();
  const jobReturnValueColumns = resolvedColumns.filter((column) => isJobReturnValueColumn(column)).sort();
  return [
    { label: "overrides", columns: overrides },
    { label: "job_return_value", columns: jobReturnValueColumns },
  ].filter((section) => section.columns.length > 0);
}

/**
 * Build the plain row model for one grouped evaluation row.
 *
 * @param {object} options - Evaluation-group row inputs.
 * @param {{groupId: string, evaluations?: Array<object>}} options.group - Evaluation group.
 * @param {Iterable<string>} options.orderedColumns - Ordered evaluation columns.
 * @param {object} options.evalTabState - Active evaluation-tab state.
 * @param {boolean} [options.isExpanded=false] - Whether the group is expanded.
 * @param {boolean} [options.isSelected=false] - Whether the group row is selected.
 * @param {(evaluations: Array<object>, getter: (evaluation: object) => string) => string} options.getGroupValueDisplayFromEvaluations - Group-value formatter.
 * @param {(evaluation: object, column: string, evalTabState: object) => string} options.getEvaluationEffectiveValue - Effective-value formatter.
 * @returns {{groupId: string, groupSize: number, isExpanded: boolean, isSelected: boolean, valueCells: Array<{column: string, content: string}>, runDirValue: string}} Plain row model.
 */
export function buildEvaluationGroupRowModel({
  group,
  orderedColumns,
  evalTabState,
  isExpanded = false,
  isSelected = false,
  getGroupValueDisplayFromEvaluations,
  getEvaluationEffectiveValue,
}) {
  return {
    groupId: group.groupId,
    groupSize: Array.isArray(group.evaluations) ? group.evaluations.length : 0,
    isExpanded,
    isSelected,
    valueCells: Array.from(orderedColumns || []).map((column) => ({
      column,
      content: getGroupValueDisplayFromEvaluations(group.evaluations || [], (evaluation) =>
        getEvaluationEffectiveValue(evaluation, column, evalTabState)
      ),
    })),
    runDirValue: getGroupValueDisplayFromEvaluations(
      group.evaluations || [],
      (evaluation) => evaluation.runDir
    ),
  };
}

/**
 * Build the plain row model for one expanded evaluation-member row.
 *
 * @param {object} options - Evaluation-member row inputs.
 * @param {object} options.evaluation - Evaluation member entry.
 * @param {Iterable<string>} options.orderedColumns - Ordered evaluation columns.
 * @param {object} options.evalTabState - Active evaluation-tab state.
 * @param {boolean} [options.isSelected=false] - Whether the member row is selected.
 * @param {(evaluation: object, column: string, evalTabState: object) => string} options.getEvaluationEffectiveValue - Effective-value formatter.
 * @returns {{runDir: string, runDirValue: string, isSelected: boolean, groupSizeLabel: string, valueCells: Array<{column: string, content: string}>}} Plain member-row model.
 */
export function buildEvaluationMemberRowModel({
  evaluation,
  orderedColumns,
  evalTabState,
  isSelected = false,
  getEvaluationEffectiveValue,
}) {
  return {
    runDir: evaluation.runDir,
    runDirValue: normalizeValue(evaluation.runDir),
    isSelected,
    groupSizeLabel: "member",
    valueCells: Array.from(orderedColumns || []).map((column) => ({
      column,
      content: getEvaluationEffectiveValue(evaluation, column, evalTabState),
    })),
  };
}

/**
 * Append one ordered set of truncating evaluation value cells to the provided row element.
 *
 * @param {object} options - Row-cell render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLTableRowElement} options.rowElement - Row receiving the cells.
 * @param {Array<{column: string, content: string}>} options.valueCells - Plain value-cell models.
 * @param {Set<string>} options.truncateEnabledColumns - Enabled truncation columns.
 * @returns {void}
 */
function appendEvaluationValueCells({
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
 * Render the evaluation-table header rows.
 *
 * @param {object} options - Header render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {Array<{label: string, columns: string[]}>} options.evalColumnSections - Evaluation column sections.
 * @param {Iterable<string>} options.orderedEvalColumns - Ordered evaluation columns.
 * @param {object} options.evalTabState - Active evaluation-tab state.
 * @param {(column: string) => string} options.displayColumnName - Header-label formatter.
 * @param {(column: string, event: Event) => void} options.onSortToggle - Sort toggle callback.
 * @param {(column: string, checked: boolean) => void} options.onToggleGroupByColumn - Group-by toggle callback.
 * @param {(checked: boolean, displayedGroupIds: string[]) => void} options.onSelectAllDisplayed - Select-all callback.
 * @param {{displayedGroupIds: string[], selectedCount: number, allSelected: boolean, someSelected: boolean}} options.selectionState - Shared selection state.
 * @param {Set<string>} options.sortableControlColumns - Control columns that default to descending order.
 * @returns {HTMLTableSectionElement} The rendered table header.
 */
function renderEvaluationTableHead({
  documentLike,
  evalColumnSections,
  orderedEvalColumns,
  evalTabState,
  displayColumnName,
  onSortToggle,
  onToggleGroupByColumn,
  onSelectAllDisplayed,
  selectionState,
  sortableControlColumns,
}) {
  const groupByFieldSet = new Set(evalTabState.groupByFields || []);
  const thead = documentLike.createElement("thead");
  const sectionRow = documentLike.createElement("tr");
  sectionRow.appendChild(
    createStaticControlHeaderCell({
      documentLike,
      label: "expand",
      column: "expand",
      sortConfig: evalTabState.sort,
      onToggle: (event) => onSortToggle("expand", event),
      sortableControlColumns,
    })
  );
  sectionRow.appendChild(
    createSelectHeaderCell({
      documentLike,
      sortConfig: evalTabState.sort,
      onToggle: (event) => onSortToggle("select", event),
      selectionState,
      onSelectAllToggle: (checked) => onSelectAllDisplayed(checked, selectionState.displayedGroupIds),
      sortableControlColumns,
      checkboxTitle: "Select or deselect all displayed evaluation groups",
      checkboxAriaLabel: "Select or deselect all displayed evaluation groups",
    })
  );
  sectionRow.appendChild(
    createStaticControlHeaderCell({
      documentLike,
      label: "#",
      column: "group_size",
      sortConfig: evalTabState.sort,
      onToggle: (event) => onSortToggle("group_size", event),
      sortableControlColumns,
    })
  );

  if ((evalColumnSections || []).length > 0) {
    for (const section of evalColumnSections || []) {
      const th = documentLike.createElement("th");
      th.className = "section-header";
      th.colSpan = section.columns.length;
      th.textContent = section.label;
      sectionRow.appendChild(th);
    }
  } else {
    const th = documentLike.createElement("th");
    th.className = "section-header";
    th.colSpan = 1;
    th.textContent = "evaluation";
    sectionRow.appendChild(th);
  }

  const evalRunDirSection = documentLike.createElement("th");
  evalRunDirSection.className = "section-header";
  evalRunDirSection.colSpan = 1;
  evalRunDirSection.textContent = "meta";
  sectionRow.appendChild(evalRunDirSection);
  thead.appendChild(sectionRow);

  const columnRow = documentLike.createElement("tr");
  if (Array.from(orderedEvalColumns || []).length > 0) {
    for (const column of orderedEvalColumns || []) {
      const th = documentLike.createElement("th");
      th.setAttribute("aria-sort", getAriaSort(evalTabState.sort, column));
      if (evalTabState.truncateEnabledColumns?.has(column)) {
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
          sortConfig: evalTabState.sort,
          onToggle: (event) => onSortToggle(column, event),
          sortableControlColumns,
        })
      );
      th.style.minWidth = `${Math.max(140, headerLabel.length * 8)}px`;
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
  } else {
    const th = documentLike.createElement("th");
    th.textContent = "(no evaluation columns)";
    columnRow.appendChild(th);
  }

  const runDirTh = documentLike.createElement("th");
  runDirTh.setAttribute("aria-sort", getAriaSort(evalTabState.sort, "eval_run_dir"));
  if (evalTabState.truncateEnabledColumns?.has("eval_run_dir")) {
    runDirTh.classList.add("truncate-enabled");
  }
  runDirTh.appendChild(
    createSortButton({
      documentLike,
      label: "eval_run_dir",
      column: "eval_run_dir",
      sortConfig: evalTabState.sort,
      onToggle: (event) => onSortToggle("eval_run_dir", event),
      sortableControlColumns,
    })
  );
  runDirTh.style.minWidth = "240px";
  columnRow.appendChild(runDirTh);
  thead.appendChild(columnRow);
  return thead;
}

/**
 * Render the evaluation table body rows from grouped and member-row models.
 *
 * @param {object} options - Body render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {Iterable<object>} options.displayedGroups - Displayed evaluation groups.
 * @param {Iterable<string>} options.orderedEvalColumns - Ordered evaluation columns.
 * @param {object} options.evalTabState - Active evaluation-tab state.
 * @param {(groupId: string) => void} options.onGroupRowSelect - Group-row selection callback.
 * @param {(groupId: string) => void} options.onToggleGroupExpansion - Expand-toggle callback.
 * @param {(groupId: string, checked: boolean) => void} options.onToggleGroupSelection - Group-selection callback.
 * @param {(runDir: string) => void} options.onMemberRowSelect - Member-row selection callback.
 * @param {(evaluations: Array<object>, getter: (evaluation: object) => string) => string} options.getGroupValueDisplayFromEvaluations - Group-value formatter.
 * @param {(evaluation: object, column: string, evalTabState: object) => string} options.getEvaluationEffectiveValue - Effective-value formatter.
 * @param {(evaluations: Array<object>, evalTabState: object) => Array<object>} options.getSortedEvaluations - Evaluation sorter.
 * @returns {HTMLTableSectionElement} The rendered table body.
 */
function renderEvaluationTableBody({
  documentLike,
  displayedGroups,
  orderedEvalColumns,
  evalTabState,
  onGroupRowSelect,
  onToggleGroupExpansion,
  onToggleGroupSelection,
  onMemberRowSelect,
  getGroupValueDisplayFromEvaluations,
  getEvaluationEffectiveValue,
  getSortedEvaluations,
}) {
  const tbody = documentLike.createElement("tbody");
  for (const group of displayedGroups || []) {
    const groupModel = buildEvaluationGroupRowModel({
      group,
      orderedColumns: orderedEvalColumns,
      evalTabState,
      isExpanded: evalTabState.expandedGroupIds.has(group.groupId),
      isSelected: group.groupId === evalTabState.selectedEvalGroupId,
      getGroupValueDisplayFromEvaluations,
      getEvaluationEffectiveValue,
    });
    const tr = documentLike.createElement("tr");
    tr.style.cursor = "pointer";
    if (groupModel.isSelected) {
      tr.classList.add("eval-row-selected");
    }
    tr.addEventListener("click", () => onGroupRowSelect(group.groupId));

    const expandTd = documentLike.createElement("td");
    const expandButton = documentLike.createElement("button");
    expandButton.type = "button";
    expandButton.className = "expand-button";
    expandButton.textContent = groupModel.isExpanded ? "-" : "+";
    expandButton.title = groupModel.isExpanded ? "Collapse group members" : "Expand group members";
    expandButton.addEventListener("click", (event) => {
      event.stopPropagation();
      onToggleGroupExpansion(group.groupId);
    });
    expandTd.appendChild(expandButton);
    tr.appendChild(expandTd);

    const selectTd = documentLike.createElement("td");
    const checkbox = documentLike.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = evalTabState.selectedGroupIds.has(group.groupId);
    checkbox.addEventListener("click", (event) => event.stopPropagation());
    checkbox.addEventListener("change", () => onToggleGroupSelection(group.groupId, checkbox.checked));
    selectTd.appendChild(checkbox);
    tr.appendChild(selectTd);

    tr.appendChild(
      createTruncatingCell({
        documentLike,
        content: String(groupModel.groupSize),
      })
    );
    if (groupModel.valueCells.length === 0) {
      tr.appendChild(createTruncatingCell({ documentLike, content: "" }));
    }
    appendEvaluationValueCells({
      documentLike,
      rowElement: tr,
      valueCells: groupModel.valueCells,
      truncateEnabledColumns: evalTabState.truncateEnabledColumns,
    });
    tr.appendChild(
      createTruncatingCell({
        documentLike,
        content: groupModel.runDirValue,
        columnKey: "eval_run_dir",
        truncateEnabledColumns: evalTabState.truncateEnabledColumns,
      })
    );
    tbody.appendChild(tr);

    if (!groupModel.isExpanded) {
      continue;
    }

    const sortedMembers = getSortedEvaluations(group.evaluations || [], evalTabState);
    for (const evaluation of sortedMembers) {
      const memberModel = buildEvaluationMemberRowModel({
        evaluation,
        orderedColumns: orderedEvalColumns,
        evalTabState,
        isSelected: evaluation.runDir === evalTabState.selectedEvalRunDir,
        getEvaluationEffectiveValue,
      });
      const memberRow = documentLike.createElement("tr");
      memberRow.className = "member-row";
      memberRow.style.cursor = "pointer";
      if (memberModel.isSelected) {
        memberRow.classList.add("eval-row-selected");
      }
      memberRow.addEventListener("click", () => onMemberRowSelect(memberModel.runDir));
      memberRow.appendChild(createTruncatingCell({ documentLike, content: "" }));
      memberRow.appendChild(createTruncatingCell({ documentLike, content: "" }));
      memberRow.appendChild(
        createTruncatingCell({
          documentLike,
          content: memberModel.groupSizeLabel,
        })
      );
      if (memberModel.valueCells.length === 0) {
        memberRow.appendChild(createTruncatingCell({ documentLike, content: "" }));
      }
      appendEvaluationValueCells({
        documentLike,
        rowElement: memberRow,
        valueCells: memberModel.valueCells,
        truncateEnabledColumns: evalTabState.truncateEnabledColumns,
      });
      memberRow.appendChild(
        createTruncatingCell({
          documentLike,
          content: memberModel.runDirValue,
          columnKey: "eval_run_dir",
          truncateEnabledColumns: evalTabState.truncateEnabledColumns,
        })
      );
      tbody.appendChild(memberRow);
    }
  }
  return tbody;
}

/**
 * Render the full evaluation table from selector-derived evaluation groups.
 *
 * @param {object} options - Evaluation-table render inputs.
 * @param {Document} [options.documentLike=globalThis.document] - Document-like element factory.
 * @param {HTMLTableElement | null} options.tableElement - Target table element.
 * @param {Array<{label: string, columns: string[]}>} options.evalColumnSections - Evaluation column sections.
 * @param {Iterable<string>} options.orderedEvalColumns - Ordered evaluation columns.
 * @param {Iterable<object>} options.displayedGroups - Displayed evaluation groups.
 * @param {object} options.evalTabState - Active evaluation-tab state.
 * @param {(column: string) => string} options.displayColumnName - Header-label formatter.
 * @param {(column: string, event: Event) => void} options.onSortToggle - Sort toggle callback.
 * @param {(column: string, checked: boolean) => void} options.onToggleGroupByColumn - Group-by toggle callback.
 * @param {(checked: boolean, displayedGroupIds: string[]) => void} options.onSelectAllDisplayed - Select-all callback.
 * @param {(groupId: string) => void} options.onGroupRowSelect - Group-row selection callback.
 * @param {(groupId: string) => void} options.onToggleGroupExpansion - Expand-toggle callback.
 * @param {(groupId: string, checked: boolean) => void} options.onToggleGroupSelection - Group-selection callback.
 * @param {(runDir: string) => void} options.onMemberRowSelect - Member-row selection callback.
 * @param {(evaluations: Array<object>, getter: (evaluation: object) => string) => string} options.getGroupValueDisplayFromEvaluations - Group-value formatter.
 * @param {(evaluation: object, column: string, evalTabState: object) => string} options.getEvaluationEffectiveValue - Effective-value formatter.
 * @param {(evaluations: Array<object>, evalTabState: object) => Array<object>} options.getSortedEvaluations - Evaluation sorter.
 * @param {Set<string>} options.sortableControlColumns - Control columns that default to descending order.
 * @returns {{displayedGroupIds: string[], selectedCount: number, allSelected: boolean, someSelected: boolean}} The rendered selection state.
 */
export function renderEvaluationTable({
  documentLike = globalThis.document,
  tableElement,
  evalColumnSections,
  orderedEvalColumns,
  displayedGroups,
  evalTabState,
  displayColumnName,
  onSortToggle,
  onToggleGroupByColumn,
  onSelectAllDisplayed,
  onGroupRowSelect,
  onToggleGroupExpansion,
  onToggleGroupSelection,
  onMemberRowSelect,
  getGroupValueDisplayFromEvaluations,
  getEvaluationEffectiveValue,
  getSortedEvaluations,
  sortableControlColumns,
}) {
  const selectionState = buildSelectionState(
    Array.from(displayedGroups || []).map((group) => group.groupId),
    evalTabState.selectedGroupIds
  );
  if (!tableElement) {
    return selectionState;
  }
  tableElement.innerHTML = "";
  tableElement.appendChild(
    renderEvaluationTableHead({
      documentLike,
      evalColumnSections,
      orderedEvalColumns,
      evalTabState,
      displayColumnName,
      onSortToggle,
      onToggleGroupByColumn,
      onSelectAllDisplayed,
      selectionState,
      sortableControlColumns,
    })
  );
  tableElement.appendChild(
    renderEvaluationTableBody({
      documentLike,
      displayedGroups,
      orderedEvalColumns,
      evalTabState,
      onGroupRowSelect,
      onToggleGroupExpansion,
      onToggleGroupSelection,
      onMemberRowSelect,
      getGroupValueDisplayFromEvaluations,
      getEvaluationEffectiveValue,
      getSortedEvaluations,
    })
  );
  return selectionState;
}
