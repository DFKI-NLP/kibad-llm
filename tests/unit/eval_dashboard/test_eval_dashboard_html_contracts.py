"""Durable HTML contract smoke tests for the pre-refactor eval dashboard page."""

import hashlib
import json
import re

from kibad_llm.config import PROJ_ROOT
from tests import FIXTURE_DATA_ROOT

DASHBOARD_ENTRY = PROJ_ROOT / "docs" / "eval-dashboard" / "index.html"
BASELINE_SUMMARY = FIXTURE_DATA_ROOT / "eval_dashboard" / "baseline" / "baseline-summary.json"


def _dashboard_html() -> str:
    """Return the current dashboard HTML source as text."""

    return DASHBOARD_ENTRY.read_text(encoding="utf-8")


def _baseline_summary() -> dict:
    """Return the checked-in baseline summary artifact."""

    return json.loads(BASELINE_SUMMARY.read_text(encoding="utf-8"))


def _inline_script() -> str:
    """Return the normalized inline dashboard script text."""

    html = _dashboard_html()
    match = re.search(r"<script\b[^>]*>(.*?)</script>", html, re.DOTALL)
    assert match is not None
    return match.group(1).replace("\r\n", "\n").strip()


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


def test_dashboard_html_keeps_phase_three_inline_script_fingerprint() -> None:
    """Ensure the CSS-only Phase 3 keeps the pre-Phase-4 inline script unchanged."""

    summary = _baseline_summary()
    script = _inline_script()
    phase_three_contract = summary["phase_three_contract"]

    assert len(script.splitlines()) == phase_three_contract["inline_script_line_count"]
    assert (
        hashlib.sha256(script.encode("utf-8")).hexdigest()
        == phase_three_contract["inline_script_sha256"]
    )
