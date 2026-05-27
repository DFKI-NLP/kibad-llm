from pathlib import Path
import subprocess  # nosec B404
import sys

from kibad_llm.config import PROJ_ROOT

SITE_ROOT = PROJ_ROOT / "site"


def test_eval_dashboard_docs_build_succeeds() -> None:
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
