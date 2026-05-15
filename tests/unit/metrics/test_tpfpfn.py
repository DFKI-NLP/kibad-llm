import json

import pytest

from kibad_llm.metrics.tpfpfn import TpFpFnCollector


def test_compute_returns_tpfpfn_entries_with_record_ids() -> None:
    m = TpFpFnCollector()

    m.update(prediction=["A", "B"], reference=["A", "C"], record_id="record-1")
    m.update(prediction=["A"], reference=["A"], record_id="record-2")

    assert m.compute(reset=False) == {
        "tp": [["record-1", "A"], ["record-2", "A"]],
        "fp": [["record-1", "B"]],
        "fn": [["record-1", "C"]],
    }


def test_compute_groups_entries_per_record() -> None:
    m = TpFpFnCollector(per_record=True)

    m.update(prediction=["A", "B"], reference=["A", "C"], record_id="record-1")
    m.update(prediction=["A"], reference=["A", "D"], record_id="record-2")

    assert m.compute(reset=False) == {
        "record-1": {"tp": ["A"], "fp": ["B"], "fn": ["C"]},
        "record-2": {"tp": ["A"], "fp": [], "fn": ["D"]},
    }


@pytest.mark.parametrize("per_record", [False, True])
def test_compute_output_is_json_roundtrip_stable(per_record) -> None:
    m = TpFpFnCollector(per_record=per_record, field="items")

    m.update(
        prediction={"items": [{"label": "A"}, {"label": "B"}]},
        reference={"items": [{"label": "A"}, {"label": "C"}]},
        record_id="record-1",
    )

    result = m._compute()

    assert result == json.loads(json.dumps(result))
