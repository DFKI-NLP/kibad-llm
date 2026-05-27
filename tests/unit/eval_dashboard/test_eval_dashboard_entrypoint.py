"""Structural smoke tests for the eval dashboard docs entrypoint."""

import yaml

from kibad_llm.config import PROJ_ROOT
from tests import FIXTURE_DATA_ROOT

DOCS_ROOT = PROJ_ROOT / "docs"
DOCS_INDEX = DOCS_ROOT / "index.md"
DASHBOARD_ENTRY = DOCS_ROOT / "eval-dashboard" / "index.html"
DASHBOARD_COMPAT = DOCS_ROOT / "eval-dashboard.html"
PROPERDOCS_CONFIG = PROJ_ROOT / "properdocs.yml"
BASELINE_MANIFEST = FIXTURE_DATA_ROOT / "eval_dashboard" / "baseline" / "baseline-manifest.md"
BASELINE_SUMMARY = FIXTURE_DATA_ROOT / "eval_dashboard" / "baseline" / "baseline-summary.json"


def _load_properdocs() -> dict:
    """Load the ProperDocs configuration for entrypoint assertions."""

    return yaml.safe_load(PROPERDOCS_CONFIG.read_text(encoding="utf-8"))


def test_dashboard_entrypoint_exists() -> None:
    """Ensure the new dashboard entrypoint and compatibility shim both exist."""

    assert DASHBOARD_ENTRY.is_file()
    assert DASHBOARD_COMPAT.is_file()


def test_phase_zero_baseline_artifacts_exist() -> None:
    """Ensure the baseline artifacts established before refactoring are present."""

    assert BASELINE_MANIFEST.is_file()
    assert BASELINE_SUMMARY.is_file()


def test_properdocs_nav_points_to_new_dashboard_entry() -> None:
    """Ensure docs navigation points to the folder-based dashboard entrypoint."""

    config = _load_properdocs()
    assert {"Evaluation dashboard": "eval-dashboard/index.html"} in config["nav"]


def test_docs_index_links_point_to_new_dashboard_entry() -> None:
    """Ensure docs landing-page links target the new dashboard path only."""

    text = DOCS_INDEX.read_text(encoding="utf-8")
    assert "(eval-dashboard/index.html)" in text
    assert "(eval-dashboard.html)" not in text


def test_old_dashboard_path_has_redirect_coverage() -> None:
    """Ensure the legacy dashboard path still redirects to the new entrypoint."""

    compat_html = DASHBOARD_COMPAT.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' in compat_html
    assert "eval-dashboard/index.html" in compat_html
