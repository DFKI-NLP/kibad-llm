import pytest

from kibad_llm.extractors.union import (
    _aggregate_structured_outputs_union,
    _multi_entry_union,
    _union_single,
)


class TestUnionSingle:
    def test_all_same_values(self):
        assert _union_single([1, 1, 1]) == 1
        assert _union_single(["a", "a"]) == "a"

    def test_with_none_values(self):
        assert _union_single([1, None, 1]) == 1
        assert _union_single([None, "a", None, "a"]) == "a"

    def test_all_none(self):
        assert _union_single([None, None]) is None

    def test_empty_list(self):
        assert _union_single([]) is None

    def test_conflicting_values(self):
        with pytest.raises(ValueError, match="Conflicting values"):
            _union_single([1, 2, 3])


class TestMultiEntryUnion:
    def test_union_of_lists(self):
        result = _multi_entry_union([[1, 2], [2, 3], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_with_none_lists(self):
        result = _multi_entry_union([[1, 2], None, [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_with_dicts(self):
        result = _multi_entry_union([[{"a": 1}, {"b": 2}], [{"a": 1}]])
        assert result == [{"a": 1}, {"b": 2}]

    def test_empty_lists(self):
        assert _multi_entry_union([[], []]) == []


class TestAggregateStructuredOutputs:
    def test_primitive_types(self):
        outputs = [{"name": "John", "age": 30}, {"name": "John"}]
        result = _aggregate_structured_outputs_union(outputs)
        assert result == {"name": "John", "age": 30}

    def test_list_union(self):
        outputs = [{"tags": ["a", "b"]}, {"tags": ["b", "c"]}]
        result = _aggregate_structured_outputs_union(outputs)
        assert result == {"tags": ["a", "b", "c"]}

    def test_all_none(self):
        assert _aggregate_structured_outputs_union([None, None]) is None

    def test_type_mismatch_raises(self):
        outputs = [{"value": 1}, {"value": "string"}]
        with pytest.raises(ValueError, match="Inconsistent types"):
            _aggregate_structured_outputs_union(outputs)

    def test_type_mismatch_skip(self):
        outputs = [{"value": 1}, {"value": "string"}]
        result = _aggregate_structured_outputs_union(outputs, skip_type_mismatches=True)
        assert result == {"value": None}

    def test_conflicting_primitives(self):
        outputs = [{"name": "John"}, {"name": "Jane"}]
        with pytest.raises(ValueError, match="Conflicting values"):
            _aggregate_structured_outputs_union(outputs)
