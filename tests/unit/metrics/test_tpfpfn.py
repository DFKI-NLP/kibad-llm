from kibad_llm.metrics.tpfpfn import TpFpFnCollector


def test_compute_returns_tpfpfn_entries_with_record_ids() -> None:
    m = TpFpFnCollector()

    m.update(prediction=["A", "B"], reference=["A", "C"], record_id="record-1")
    m.update(prediction=["A"], reference=["A"], record_id="record-2")

    assert m.compute(reset=False) == {
        "tp": {("record-1", "A"), ("record-2", "A")},
        "fp": {("record-1", "B")},
        "fn": {("record-1", "C")},
    }


def test_compute_groups_entries_per_record() -> None:
    m = TpFpFnCollector(per_record=True)

    m.update(prediction=["A", "B"], reference=["A", "C"], record_id="record-1")
    m.update(prediction=["A"], reference=["A", "D"], record_id="record-2")

    assert m.compute(reset=False) == {
        "record-1": {"tp": {"A"}, "fp": {"B"}, "fn": {"C"}},
        "record-2": {"tp": {"A"}, "fp": set(), "fn": {"D"}},
    }
