"""Browser-free logic tests for Phase 5 eval-dashboard utility modules."""

import json
from pathlib import Path
import subprocess  # nosec B404 -- controlled test-only Node.js invocation for local utility modules.
import textwrap

import pytest

from kibad_llm.config import PROJ_ROOT

UTILS_ROOT = PROJ_ROOT / "docs" / "eval-dashboard" / "assets" / "js" / "utils"


def _run_js_expression(tmp_path: Path, expression: str):
    """Execute a small ESM script in Node and return the JSON-decoded result.

    Args:
        tmp_path: Temporary pytest directory used to hold the transient script.
        expression: JavaScript expression assigned to `result` and serialized as JSON.

    Returns:
        The JSON-decoded value printed by the temporary Node.js script.
    """

    node_binary = "node"
    try:
        subprocess.run(  # nosec B603 -- fixed executable/args used only to detect local Node availability.
            [node_binary, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("Node.js is required for eval-dashboard JS utility tests.")

    script_path = tmp_path / "eval_dashboard_utils_test.mjs"
    script_path.write_text(
        textwrap.dedent(
            f"""
            import {{ flattenObject }} from {json.dumps((UTILS_ROOT / 'flatten.js').as_uri())};
            import {{ compareSortableValues, normalizeSortConfig, sortItems }} from {json.dumps((UTILS_ROOT / 'sort.js').as_uri())};
            import {{ getFigureTitlePrefix, sanitizeFigureFilename, splitLabelByLastDot }} from {json.dumps((UTILS_ROOT / 'text.js').as_uri())};
            import {{ collectSuggestionValues, getEffectiveValue, isMissingValue, normalizeValue }} from {json.dumps((UTILS_ROOT / 'values.js').as_uri())};

            const result = {expression};
            console.log(JSON.stringify(result));
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(  # nosec B603 -- fixed test harness executes a temporary script with checked-in module imports.
        [str(node_binary), str(script_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_flatten_object_flattens_nested_objects_and_serializes_arrays(tmp_path: Path) -> None:
    """Ensure `flattenObject` preserves the current nested-object and array behavior."""

    result = _run_js_expression(
        tmp_path,
        "flattenObject({ alpha: { beta: 3 }, gamma: [1, 2], delta: null }, 'root')",
    )

    assert result == {
        "root.alpha.beta": 3,
        "root.gamma": "[1,2]",
        "root.delta": None,
    }


def test_sort_helpers_normalize_and_sort_stably(tmp_path: Path) -> None:
    """Ensure the extracted sort helpers keep blank-last, numeric, and stable ordering behavior."""

    result = _run_js_expression(
        tmp_path,
        textwrap.dedent(
            """
            (() => {
              const items = [
                { name: 'item-1', value: '10' },
                { name: 'item-2', value: '' },
                { name: 'item-3', value: '2' },
                { name: 'item-4', value: '2' },
              ];
              return {
                normalized: normalizeSortConfig(
                  [
                    { column: 'value', direction: 'asc' },
                    { column: 'value', direction: 'desc' },
                    { column: 'ignored', direction: 'asc' },
                    { column: 'name', direction: 'sideways' },
                  ],
                  ['value', 'name']
                ),
                comparisons: {
                  blank_vs_value: compareSortableValues('', '3'),
                  numeric_order: compareSortableValues('2', '10'),
                  lexical_casefold: compareSortableValues('Beta', 'alpha'),
                },
                sorted_names: sortItems(
                  items,
                  [{ column: 'value', direction: 'asc' }],
                  (item, column) => item[column]
                ).map((item) => item.name),
              };
            })()
            """
        ).strip(),
    )

    assert result["normalized"] == [{"column": "value", "direction": "asc"}]
    assert result["comparisons"]["blank_vs_value"] > 0
    assert result["comparisons"]["numeric_order"] < 0
    assert result["comparisons"]["lexical_casefold"] > 0
    assert result["sorted_names"] == ["item-3", "item-4", "item-1", "item-2"]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("normalizeValue({ foo: 'bar' })", '{"foo":"bar"}'),
        ("isMissingValue('   ')", True),
        ("getEffectiveValue('', 'fallback')", "fallback"),
        (
            "collectSuggestionValues(['beta', '', 'Alpha', 'beta', null])",
            ["Alpha", "beta"],
        ),
    ],
)
def test_value_helpers_keep_normalization_and_defaulting_behavior(
    tmp_path: Path, expression: str, expected
) -> None:
    """Ensure the extracted value helpers preserve normalization and suggestion behavior."""

    result = _run_js_expression(tmp_path, expression)

    assert result == expected


def test_text_helpers_keep_plot_title_and_filename_behavior(tmp_path: Path) -> None:
    """Ensure filename/title sanitization and dotted-label shortening stay behavior-equivalent."""

    result = _run_js_expression(
        tmp_path,
        textwrap.dedent(
            """
            ({
              title_prefix: getFigureTitlePrefix('Accuracy (mean ± std) (4 grouped evals per cell)'),
              sanitized_filename: sanitizeFigureFilename('  bad<>:"/\\|?* name.  '),
              split_label: splitLabelByLastDot('metric.section.score'),
            })
            """
        ).strip(),
    )

    assert result == {
        "title_prefix": "Accuracy",
        "sanitized_filename": "bad - name",
        "split_label": "score",
    }
