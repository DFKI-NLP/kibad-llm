"""Baseline artifact contract tests for the eval dashboard refactor baseline and freeze contracts."""

import hashlib
import json

from kibad_llm.config import PROJ_ROOT
from tests import FIXTURE_DATA_ROOT

DASHBOARD_ENTRY = PROJ_ROOT / "docs" / "eval-dashboard" / "index.html"
CSS_ROOT = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "css"
JS_ROOT = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js"
CSS_ENTRY = CSS_ROOT / "index.css"
MAIN_JS_ENTRY = JS_ROOT / "main.js"
TOKENS_CSS = CSS_ROOT / "tokens.css"
BASELINE_SUMMARY = FIXTURE_DATA_ROOT / "eval_dashboard" / "baseline" / "baseline-summary.json"
FIXTURE_ROOT = FIXTURE_DATA_ROOT / "eval_dashboard"

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


def _css_entry() -> str:
    """Load the Phase 3 CSS entry file."""

    return CSS_ENTRY.read_text(encoding="utf-8")


def _tokens_css() -> str:
    """Load the dashboard theme tokens stylesheet."""

    return TOKENS_CSS.read_text(encoding="utf-8")


def _normalized_main_js() -> str:
    """Load the Phase 4 external main.js file using the frozen normalization contract."""

    return MAIN_JS_ENTRY.read_text(encoding="utf-8").replace("\r\n", "\n").strip()


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
    """Ensure the baseline artifact exposes the Phase 4 external-main.js freeze contract."""

    summary = _baseline_summary()
    phase_four_contract = summary["phase_four_contract"]

    assert phase_four_contract["main_js_path"] == "docs/eval-dashboard/assets/js/main.js"
    assert phase_four_contract["main_js_normalization"]
    assert phase_four_contract["main_js_line_count"] > 0
    assert len(phase_four_contract["main_js_sha256"]) == 64


def test_current_runtime_main_js_matches_phase_four_contract() -> None:
    """Ensure the externalized dashboard main.js stays content-equivalent to the frozen Phase 4 contract."""

    summary = _baseline_summary()
    main_js = _normalized_main_js()
    phase_four_contract = summary["phase_four_contract"]

    assert len(main_js.splitlines()) == phase_four_contract["main_js_line_count"]
    assert (
        hashlib.sha256(main_js.encode("utf-8")).hexdigest()
        == phase_four_contract["main_js_sha256"]
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
