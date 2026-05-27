"""Durable HTML contract smoke tests for the pre-refactor eval dashboard page."""

import re

from kibad_llm.config import PROJ_ROOT

DASHBOARD_ENTRY = PROJ_ROOT / "docs" / "eval-dashboard" / "index.html"


def _dashboard_html() -> str:
    """Return the current dashboard HTML source as text."""

    return DASHBOARD_ENTRY.read_text(encoding="utf-8")


def test_dashboard_html_uses_external_css_and_keeps_single_inline_script_block() -> None:
    """Ensure Phase 3 moved CSS out while keeping the single inline script until Phase 4."""

    html = _dashboard_html()

    assert 'rel="stylesheet"' in html
    assert 'href="assets/css/index.css"' in html
    assert len(re.findall(r"<style\b", html)) == 0
    assert html.count("</style>") == 0
    assert len(re.findall(r"<script\b", html)) == 1
    assert html.count("</script>") == 1
    assert re.search(r"<script\b[^>]*src=", html) is None


def test_dashboard_html_contains_load_control_anchors() -> None:
    """Ensure the load controls keep their stable DOM anchors."""

    html = _dashboard_html()

    for snippet in (
        "<h1>Evaluation Dashboard</h1>",
        'id="folderInput"',
        'id="gitUrlInput"',
        'id="githubTokenInput"',
        'id="loadGitButton"',
        'id="loadStatus"',
        'id="loadProgress"',
        'id="loadProgressLabel"',
    ):
        assert snippet in html


def test_dashboard_html_contains_prediction_section_anchors() -> None:
    """Ensure the predictions section keeps the anchors that later phases must preserve."""

    html = _dashboard_html()

    for snippet in (
        "<h2>Predictions</h2>",
        'id="predictionSummary"',
        'id="predictionDefaultsPanel"',
        'id="groupByAllButton"',
        'id="groupByNoneButton"',
        'id="groupByToggleButton"',
        'id="predictionSortedByLabel"',
        'id="predictionResetSortButton"',
        'id="predictionsTable"',
    ):
        assert snippet in html


def test_dashboard_html_contains_evaluation_section_anchors() -> None:
    """Ensure the evaluations section keeps stable anchors for tabs, table, and JSON pane."""

    html = _dashboard_html()

    for snippet in (
        "<h2>Evaluations</h2>",
        'id="evalTabs"',
        'id="evalSummary"',
        'id="evaluationsTable"',
        'id="evalJsonPane"',
        'id="evalJsonTabEvaluation"',
        'id="evalJsonTabPrediction"',
        'id="evalJsonTitle"',
        'id="evalJsonCode"',
    ):
        assert snippet in html


def test_dashboard_html_contains_plot_and_export_anchors() -> None:
    """Ensure plotting and export hooks remain present before modular extraction."""

    html = _dashboard_html()

    for snippet in (
        'id="evalPlotTabs"',
        'id="evalPlotContent"',
        'id="downloadFiguresButton"',
        'id="barTooltip"',
    ):
        assert snippet in html
