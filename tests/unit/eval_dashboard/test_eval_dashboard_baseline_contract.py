"""Baseline artifact contract tests for the eval-dashboard baseline and Phase 5 JS-test contract."""

import json

import yaml

from kibad_llm.config import PROJ_ROOT
from tests import FIXTURE_DATA_ROOT

DASHBOARD_ENTRY = PROJ_ROOT / "docs" / "eval-dashboard" / "index.html"
CSS_ROOT = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "css"
JS_ROOT = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js"
CSS_ENTRY = CSS_ROOT / "index.css"
MAIN_JS_ENTRY = JS_ROOT / "main.js"
UTILS_JS_ROOT = JS_ROOT / "utils"
TOKENS_CSS = CSS_ROOT / "tokens.css"
BASELINE_SUMMARY = FIXTURE_DATA_ROOT / "eval_dashboard" / "baseline" / "baseline-summary.json"
FIXTURE_ROOT = FIXTURE_DATA_ROOT / "eval_dashboard"
WORKFLOW_PATH = PROJ_ROOT / ".github" / "workflows" / "code_quality_and_tests.yml"
JS_TEST_ROOT = PROJ_ROOT / "tests" / "unit" / "eval_dashboard" / "js"
JS_PACKAGE_JSON = JS_ROOT / "package.json"
JS_TEST_README = JS_TEST_ROOT / "README.md"
LEGACY_JS_PYTEST_BRIDGE = JS_TEST_ROOT / "test_eval_dashboard_utils.py"

EXPECTED_FEATURE_KEYS = {
    "supports_local_load",
    "supports_github_url_load",
    "supports_prediction_grouping",
    "supports_experiment_tabs",
    "supports_json_side_pane",
    "supports_grouped_bar_plots",
    "supports_error_plots",
    "supports_confusion_matrix_plots",
    "supports_tpfpfn_plots",
    "supports_figure_export",
    "supports_light_dark_styling",
}


def _baseline_summary() -> dict:
    """Load the checked-in baseline summary artifact."""

    return json.loads(BASELINE_SUMMARY.read_text(encoding="utf-8"))


def _dashboard_html() -> str:
    """Load the current dashboard entry HTML."""

    return DASHBOARD_ENTRY.read_text(encoding="utf-8")


def _workflow_definition() -> dict:
    """Load the CI workflow that should run the dashboard JS logic tests explicitly."""

    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _main_js_entry() -> str:
    """Load the external dashboard JavaScript entry module."""

    return MAIN_JS_ENTRY.read_text(encoding="utf-8")


def _js_package_definition() -> dict:
    """Load the dashboard JS package manifest that pins ESM semantics for Node tests."""

    return json.loads(JS_PACKAGE_JSON.read_text(encoding="utf-8"))


def _js_test_readme() -> str:
    """Load the README that documents the long-term dashboard JS test harness."""

    return JS_TEST_README.read_text(encoding="utf-8")


def _css_entry() -> str:
    """Load the Phase 3 CSS entry file."""

    return CSS_ENTRY.read_text(encoding="utf-8")


def _tokens_css() -> str:
    """Load the dashboard theme tokens stylesheet."""

    return TOKENS_CSS.read_text(encoding="utf-8")


def test_baseline_summary_describes_phase_zero_reference_state() -> None:
    """Ensure the checked-in baseline remains the original pre-Phase-3 reference artifact."""

    summary = _baseline_summary()
    implementation_shape = summary["implementation_shape"]

    assert implementation_shape["runtime_entrypoint"] == "docs/eval-dashboard/index.html"
    assert implementation_shape["compatibility_entrypoint"] == "docs/eval-dashboard.html"
    assert implementation_shape["css_extraction_started"] is False
    assert implementation_shape["js_extraction_started"] is False
    assert "inline CSS" in implementation_shape["page_style"]
    assert "inline JavaScript" in implementation_shape["page_style"]


def test_baseline_summary_includes_phase_three_inline_script_contract() -> None:
    """Ensure the baseline artifact exposes the Phase 3 JS freeze contract."""

    summary = _baseline_summary()
    phase_three_contract = summary["phase_three_contract"]

    assert phase_three_contract["inline_script_normalization"]
    assert phase_three_contract["inline_script_line_count"] > 0
    assert len(phase_three_contract["inline_script_sha256"]) == 64


def test_baseline_summary_includes_phase_four_external_main_js_contract() -> None:
    """Ensure the baseline artifact still records the Phase 4 external-main.js milestone."""

    summary = _baseline_summary()
    phase_four_contract = summary["phase_four_contract"]

    assert phase_four_contract["main_js_path"] == "docs/eval-dashboard/assets/js/main.js"
    assert phase_four_contract["entrypoint_contract"]


def test_baseline_summary_includes_phase_five_utility_contract() -> None:
    """Ensure the baseline artifact exposes the Phase 5 utility-extraction contract."""

    summary = _baseline_summary()
    phase_five_contract = summary["phase_five_contract"]

    assert phase_five_contract["utility_module_root"] == "docs/eval-dashboard/assets/js/utils"
    assert phase_five_contract["js_test_root"] == "tests/unit/eval_dashboard/js"
    assert (
        phase_five_contract["js_test_strategy"]
        == "browser-free utility logic tests executed via the Node.js built-in test runner"
    )
    assert (
        phase_five_contract["js_test_command"]
        == "node --test tests/unit/eval_dashboard/js/*.test.mjs"
    )
    assert set(phase_five_contract["utility_modules"]) == {
        "flatten.js",
        "sort.js",
        "text.js",
        "values.js",
    }
    assert set(phase_five_contract["js_test_files"]) == {
        "utils.flatten.test.mjs",
        "utils.sort.test.mjs",
        "utils.text.test.mjs",
        "utils.values.test.mjs",
    }


def test_current_runtime_matches_phase_five_utility_contract() -> None:
    """Ensure the extracted Phase 5 utility modules and JS-native test assets exist."""

    summary = _baseline_summary()
    phase_five_contract = summary["phase_five_contract"]
    main_js = _main_js_entry()
    js_package = _js_package_definition()
    js_test_readme = _js_test_readme()

    assert MAIN_JS_ENTRY.is_file()
    for file_name in phase_five_contract["utility_modules"]:
        assert (UTILS_JS_ROOT / file_name).is_file()
        assert f"./utils/{file_name}" in main_js
    assert (PROJ_ROOT / phase_five_contract["js_test_root"]).is_dir()
    for file_name in phase_five_contract["js_test_files"]:
        assert (JS_TEST_ROOT / file_name).is_file()
    assert {path.name for path in JS_TEST_ROOT.glob("*.test.mjs")} == set(
        phase_five_contract["js_test_files"]
    )
    assert JS_PACKAGE_JSON.is_file()
    assert js_package == {"type": "module"}
    assert JS_TEST_README.is_file()
    assert phase_five_contract["js_test_command"] in js_test_readme
    assert "Node's built-in test runner" in js_test_readme
    assert "Keep test files flat in this directory" in js_test_readme
    assert not LEGACY_JS_PYTEST_BRIDGE.exists()
    assert not any(JS_TEST_ROOT.glob("*.py"))


def test_ci_workflow_runs_eval_dashboard_js_tests_explicitly() -> None:
    """Ensure CI exposes the dashboard JS logic tests as their own explicit Node-based check."""

    workflow = _workflow_definition()
    js_job = workflow["jobs"]["eval-dashboard-js"]
    steps = js_job["steps"]

    assert js_job["runs-on"] == "ubuntu-latest"
    assert any(step.get("uses") == "actions/setup-node@v4" for step in steps)
    assert any(
        "node --test tests/unit/eval_dashboard/js/*.test.mjs" in step.get("run", "")
        for step in steps
    )


def test_baseline_feature_expectation_keys_match_current_contract() -> None:
    """Ensure the baseline summary keeps the expected feature-expectation schema."""

    summary = _baseline_summary()

    assert set(summary["feature_expectations"]) == EXPECTED_FEATURE_KEYS


def test_current_runtime_preserves_baseline_feature_expectations() -> None:
    """Ensure each baseline feature claim is still grounded in current HTML, CSS, or fixture contracts."""

    summary = _baseline_summary()
    html = _dashboard_html()
    css_entry = _css_entry()
    tokens_css = _tokens_css()

    contract_checks = {
        "supports_local_load": lambda: 'id="folderInput"' in html,
        "supports_github_url_load": lambda: 'id="gitUrlInput"' in html
        and 'id="loadGitButton"' in html,
        "supports_prediction_grouping": lambda: all(
            snippet in html
            for snippet in (
                'id="groupByAllButton"',
                'id="groupByNoneButton"',
                'id="groupByToggleButton"',
            )
        ),
        "supports_experiment_tabs": lambda: 'id="evalTabs"' in html,
        "supports_json_side_pane": lambda: 'id="evalJsonPane"' in html,
        "supports_grouped_bar_plots": lambda: (
            FIXTURE_ROOT / "bars" / "job_return_value.json"
        ).is_file(),
        "supports_error_plots": lambda: (
            FIXTURE_ROOT / "errors" / "job_return_value.json"
        ).is_file(),
        "supports_confusion_matrix_plots": lambda: (
            FIXTURE_ROOT / "confusion_matrix" / "job_return_value.json"
        ).is_file(),
        "supports_tpfpfn_plots": lambda: (
            FIXTURE_ROOT / "tpfpfn" / "job_return_value.json"
        ).is_file(),
        "supports_figure_export": lambda: 'id="downloadFiguresButton"' in html,
        "supports_light_dark_styling": lambda: 'href="assets/css/index.css"' in html
        and "tokens.css" in css_entry
        and "prefers-color-scheme" in tokens_css
        and "color-scheme:" in tokens_css,
    }

    for feature_name, expected in summary["feature_expectations"].items():
        assert feature_name in contract_checks
        assert contract_checks[feature_name]() is expected
