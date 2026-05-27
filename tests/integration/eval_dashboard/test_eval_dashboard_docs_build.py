"""Integration smoke tests for dashboard-specific ProperDocs output.

This complements the generic ``check-mkdocs`` hook by exercising the actual
``properdocs build`` entrypoint used by this project and by asserting the
dashboard pages are emitted at the expected output paths.
"""

import subprocess  # nosec B404
import sys

from kibad_llm.config import PROJ_ROOT

SITE_ROOT = PROJ_ROOT / "site"


def test_eval_dashboard_docs_build_succeeds() -> None:
    """Verify the real ProperDocs build produces the dashboard entry pages.

    The pre-commit docs check already validates the docs configuration and a
    generic docs build path. This test keeps dashboard-focused regression
    coverage by checking the generated output files that Phase 2 depends on.
    """

    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "properdocs", "build"],
        cwd=PROJ_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise AssertionError(
            "properdocs build failed\n" f"stdout:\n{result.stdout}\n" f"stderr:\n{result.stderr}"
        )

    assert (SITE_ROOT / "eval-dashboard" / "index.html").is_file()
    assert (SITE_ROOT / "eval-dashboard.html").is_file()
