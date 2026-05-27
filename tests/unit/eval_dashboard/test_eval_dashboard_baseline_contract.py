"""Baseline artifact contract tests for the pre-Phase-3 eval dashboard state."""

import json

from kibad_llm.config import PROJ_ROOT
from tests import FIXTURE_DATA_ROOT

DASHBOARD_ENTRY = PROJ_ROOT / "docs" / "eval-dashboard" / "index.html"
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


def test_baseline_summary_describes_pre_phase_three_monolith() -> None:
    """Ensure the baseline still matches the current pre-extraction implementation shape."""

    summary = _baseline_summary()
    implementation_shape = summary["implementation_shape"]

    assert implementation_shape["runtime_entrypoint"] == "docs/eval-dashboard/index.html"
    assert implementation_shape["compatibility_entrypoint"] == "docs/eval-dashboard.html"
    assert implementation_shape["css_extraction_started"] is False
    assert implementation_shape["js_extraction_started"] is False
    assert "inline CSS" in implementation_shape["page_style"]
    assert "inline JavaScript" in implementation_shape["page_style"]


def test_baseline_feature_expectation_keys_match_current_contract() -> None:
    """Ensure the baseline summary keeps the expected feature-expectation schema."""

    summary = _baseline_summary()

    assert set(summary["feature_expectations"]) == EXPECTED_FEATURE_KEYS


def test_baseline_feature_expectations_are_backed_by_html_or_fixture_contracts() -> None:
    """Ensure each baseline feature claim is grounded in fixture coverage or durable HTML structure."""

    summary = _baseline_summary()
    html = _dashboard_html()

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
        "supports_light_dark_styling": lambda: "prefers-color-scheme" in html
        and "color-scheme:" in html,
    }

    for feature_name, expected in summary["feature_expectations"].items():
        assert feature_name in contract_checks
        assert contract_checks[feature_name]() is expected
