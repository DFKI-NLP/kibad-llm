"""Contract checks for eval-dashboard main-module orchestration boundaries."""

import re

from kibad_llm.config import PROJ_ROOT

MAIN_JS = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js" / "main.js"
SESSION_JS = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js" / "browser" / "session.js"
PREDICTION_TABLE_JS = (
    PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js" / "ui" / "prediction-table.js"
)
EVALUATION_TABLE_JS = (
    PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js" / "ui" / "evaluation-table.js"
)


def _main_js() -> str:
    """Load the eval-dashboard main entry module source."""

    return MAIN_JS.read_text(encoding="utf-8")


def _session_js() -> str:
    """Load the eval-dashboard browser-session helper source."""

    return SESSION_JS.read_text(encoding="utf-8")


def _prediction_table_js() -> str:
    """Load the eval-dashboard prediction-table helper source."""

    return PREDICTION_TABLE_JS.read_text(encoding="utf-8")


def _evaluation_table_js() -> str:
    """Load the eval-dashboard evaluation-table helper source."""

    return EVALUATION_TABLE_JS.read_text(encoding="utf-8")


def test_browser_session_module_keeps_to_session_and_query_parameter_helpers() -> None:
    """Ensure the session module no longer owns the local file-load orchestration flow."""

    session_js = _session_js()
    assert "handleLocalEvaluationFileSelection" not in session_js


def test_main_module_keeps_local_file_selection_orchestration_inline() -> None:
    """Ensure local file selection clears git_url before loading and rerendering in main.js."""

    main_js = _main_js()

    assert "handleLocalEvaluationFileSelection" not in main_js
    assert "clearGitUrlQueryParam();" in main_js
    assert "await loadEvaluationsFromFiles(files);" in main_js
    assert "renderPredictions();" in main_js
    assert "renderEvaluations();" in main_js

    match = re.search(
        r'folderInput\.addEventListener\("change", async \(event\) => \{(?P<body>.*?)\n}\);',
        main_js,
        re.DOTALL,
    )
    assert match is not None
    body = match.group("body")

    clear_index = body.index("clearGitUrlQueryParam();")
    load_index = body.index("await loadEvaluationsFromFiles(files);")
    render_predictions_index = body.index("renderPredictions();")
    render_evaluations_index = body.index("renderEvaluations();")

    assert clear_index < load_index < render_predictions_index < render_evaluations_index


def test_main_module_keeps_query_param_bootstrap_delegated_to_session_helpers() -> None:
    """Ensure GitHub query-parameter bootstrap still flows through the extracted session helper."""

    main_js = _main_js()

    assert "runGitUrlQueryParamBootstrap" in main_js
    assert "inputElement: gitUrlInput" in main_js
    assert "onLoadRequested: () => handleGitLoadRequest()" in main_js


def test_main_module_calls_phase_ten_a_tab_helpers_directly_without_local_wrapper_functions() -> (
    None
):
    """Ensure `main.js` uses the extracted tab helper directly instead of new pass-through wrappers."""

    main_js = _main_js()

    assert "function renderOptionsTabs()" not in main_js
    assert "function renderEvalOptionsTabs(activeExperiment = state.activeEvalTab)" not in main_js
    assert 'optionsTabs.addEventListener("click"' not in main_js
    assert 'evalOptionsTabs.addEventListener("click"' not in main_js
    assert "bindDelegatedTabSelection," in main_js
    assert main_js.count("bindDelegatedTabSelection({") == 2
    assert "buildCountTabButtonModels," in main_js
    assert "renderTabButtons," in main_js
    assert "renderPlotTabsAndGrid as renderSharedPlotTabsAndGrid" in main_js
    assert main_js.count("renderTabButtons({") == 3
    assert main_js.count("buildCountTabButtonModels(") == 3
    assert "buildTabButtonModels(" not in main_js
    assert main_js.count("resolveActiveTabValue(") == 3
    assert main_js.count("renderStaticTabState({") >= 3
    assert "buttonElements: optionsTabButtons" in main_js
    assert "panelElements: optionsTabPanels" in main_js
    assert "buttonElements: evalOptionsTabButtons" in main_js
    assert "panelElements: evalOptionsTabPanels" in main_js
    assert 'buttonAttribute: "data-eval-tab"' in main_js
    assert 'panelAttribute: "data-eval-tab-panel"' in main_js
    assert "containerElement: evalPlotTabs" in main_js
    assert 'button.className = "tab-button"' not in main_js
    assert "evalPlotTabs.appendChild(button);" not in main_js


def test_main_module_delegates_phase_ten_a_options_panel_rendering_to_controls_helper() -> None:
    """Ensure `main.js` no longer open-codes checkbox/default panel DOM rendering for Phase 10A controls."""

    main_js = _main_js()

    assert "renderOptionsPanel," in main_js
    assert main_js.count("renderOptionsPanel({") == 2
    assert "renderCheckboxOptionList({" not in main_js
    assert "renderMissingDefaultControls({" not in main_js
    assert "buildColumnOptions(" not in main_js
    assert "buildMissingDefaultControlModels(" not in main_js
    assert "buildOptionsPanelModels(" not in main_js
    assert "renderOptionsPanelControls({" not in main_js
    assert "checkboxColumns: orderedPredictionColumns" in main_js
    assert 'checkboxColumns: [...new Set([...orderedEvalColumns, "eval_run_dir"])]' in main_js
    assert "defaultColumns: predictionDefaultColumns" in main_js
    assert "defaultColumns: evalDefaultColumns" in main_js


def test_main_module_delegates_prediction_and_evaluation_group_by_button_state_to_controls_helper() -> (
    None
):
    """Ensure both table surfaces now reuse the shared Phase 10A group-by-button renderer."""

    main_js = _main_js()

    assert main_js.count("renderGroupByButtonState(") >= 4

    prediction_match = re.search(
        r"function renderPredictions\(\) \{(?P<body>.*?)\n}\n\n/\*\*",
        main_js,
        re.DOTALL,
    )
    assert prediction_match is not None
    prediction_body = prediction_match.group("body")
    assert "allButton: groupByAllButton" in prediction_body
    assert "toggleButton: groupByToggleButton" in prediction_body
    assert "noneButton: groupByNoneButton" in prediction_body

    evaluation_match = re.search(
        r"function renderEvaluations\(\) \{(?P<body>.*)\n}$",
        main_js,
        re.DOTALL,
    )
    assert evaluation_match is not None
    evaluation_body = evaluation_match.group("body")
    assert "allButton: evalGroupByAllButton" in evaluation_body
    assert "toggleButton: evalGroupByToggleButton" in evaluation_body
    assert "noneButton: evalGroupByNoneButton" in evaluation_body


def test_main_module_delegates_per_column_group_by_toggle_rendering_to_table_modules() -> None:
    """Ensure per-column table-header grouping now lives in the extracted Phase 10B table modules."""

    main_js = _main_js()
    prediction_table_js = _prediction_table_js()
    evaluation_table_js = _evaluation_table_js()

    assert 'from "./ui/prediction-table.js"' in main_js
    assert "renderPredictionTable," in main_js
    assert 'from "./ui/evaluation-table.js"' in main_js
    assert "renderEvaluationTable," in main_js
    assert "createGroupByToggleControl," not in main_js
    assert main_js.count("createGroupByToggleControl({") == 0
    assert prediction_table_js.count("createGroupByToggleControl({") == 1
    assert evaluation_table_js.count("createGroupByToggleControl({") == 1
    assert 'toggle.className = "group-toggle"' not in main_js
    assert 'toggle.title = "Use this column for grouping"' not in main_js
    assert "toggleCb.checked =" not in main_js
    assert 'toggleCb.addEventListener("change"' not in main_js


def test_main_module_delegates_table_section_builders_to_table_modules() -> None:
    """Ensure `main.js` no longer owns prediction/evaluation header-section builders."""

    main_js = _main_js()
    prediction_table_js = _prediction_table_js()
    evaluation_table_js = _evaluation_table_js()

    assert "function getPredictionColumnSections(" not in main_js
    assert "function getEvalColumnSections(" not in main_js
    assert "buildPredictionColumnSections," in main_js
    assert "buildEvaluationColumnSections," in main_js
    assert "const predictionSections = buildPredictionColumnSections({" in main_js
    assert "const evalColumnSections = buildEvaluationColumnSections(evalColumns, {" in main_js
    assert "export function buildPredictionColumnSections(" in prediction_table_js
    assert "export function buildEvaluationColumnSections(" in evaluation_table_js


def test_main_module_delegates_eval_json_pane_rendering_to_phase_ten_a_helper() -> None:
    """Ensure `main.js` no longer open-codes JSON highlighting and selected-content wiring."""

    main_js = _main_js()

    assert "bindEvalJsonTabSelection," in main_js
    assert main_js.count("bindEvalJsonTabSelection({") == 1
    assert main_js.count("renderEvalJsonPane({") == 2
    assert "selectedEvaluation," in main_js
    assert "selectedGroup," in main_js
    assert "getPredictionContent: reconstructPredictionContentForEvaluation" in main_js
    assert 'evalJsonTabEvaluation.addEventListener("click"' not in main_js
    assert 'evalJsonTabPrediction.addEventListener("click"' not in main_js
    assert "highlightJsonContent(" not in main_js
    assert "escapeHtml(" not in main_js


def test_main_module_delegates_thin_plot_control_rendering_to_controls_helper() -> None:
    """Ensure the remaining thin plot-control surface no longer lives inline in `main.js`."""

    main_js = _main_js()

    assert "renderPlotControls," in main_js
    assert "renderPlotGroupBarChips," in main_js
    assert "function renderPlotControls(" not in main_js
    assert "function renderGroupBarChips(" not in main_js
    assert main_js.count("renderPlotControls({") == 3
    assert main_js.count("renderPlotGroupBarChips({") == 1
    assert "plotTabsByPrefixButton," in main_js
    assert "plotConfusionTabsByRow," in main_js
    assert "plotShowLegendOnceRow," in main_js
    assert "listElement: plotGroupBarsList" in main_js
    assert "getLabel: displayPlotGroupFieldName" in main_js


def test_main_module_delegates_sort_status_rendering_to_controls_helper() -> None:
    """Ensure `main.js` no longer owns the sort-status label/reset-button rendering logic."""

    main_js = _main_js()

    assert "renderSortStatus," in main_js
    assert main_js.count("renderSortStatus({") == 3
    assert "function renderPredictionSortStatus()" not in main_js
    assert "function renderEvalSortStatus(" not in main_js
    assert "predictionSortedByLabel.textContent =" not in main_js
    assert "evalSortedByLabel.textContent =" not in main_js
    assert "predictionResetSortButton.disabled =" not in main_js
    assert "evalResetSortButton.disabled =" not in main_js
