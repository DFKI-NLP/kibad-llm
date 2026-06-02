"""Contract checks for eval-dashboard main-module orchestration boundaries."""

import re

from kibad_llm.config import PROJ_ROOT

MAIN_JS = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js" / "main.js"
SESSION_JS = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js" / "browser" / "session.js"


def _main_js() -> str:
    """Load the eval-dashboard main entry module source."""

    return MAIN_JS.read_text(encoding="utf-8")


def _session_js() -> str:
    """Load the eval-dashboard browser-session helper source."""

    return SESSION_JS.read_text(encoding="utf-8")


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
