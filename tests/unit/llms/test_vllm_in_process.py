"""Verify in-process vLLM token accounting without loading a model or using a GPU."""

import json
from typing import Any
from unittest.mock import Mock

import pytest
from vllm.outputs import CompletionOutput, RequestOutput

from kibad_llm.extractors.base import extract_from_text
from kibad_llm.llms.vllm_in_process import VllmInProcess


@pytest.mark.parametrize("prompt_token_ids", [[1, 2, 3], [], None])
@pytest.mark.parametrize("num_cached_tokens", [None, 0, 2])
def test_in_process_usage_counts_all_generated_tokens(
    monkeypatch, prompt_token_ids, num_cached_tokens
) -> None:
    """Count the full generations rather than retokenizing only the selected text."""
    monkeypatch.setattr("kibad_llm.llms.vllm_in_process.cleanup", lambda: None)
    backend = VllmInProcess(model="unused", lazy=True)
    output = RequestOutput(
        request_id="test",
        prompt="document",
        prompt_token_ids=prompt_token_ids,
        prompt_logprobs=None,
        outputs=[
            CompletionOutput(
                index=0, text="{}", token_ids=[4, 5, 6], cumulative_logprob=None, logprobs=None
            ),
            CompletionOutput(
                index=1, text="{}", token_ids=[7, 8], cumulative_logprob=None, logprobs=None
            ),
        ],
        finished=True,
        num_cached_tokens=num_cached_tokens,
    )
    monkeypatch.setattr(backend, "_llm", Mock(chat=Mock(return_value=[output])), raising=False)
    monkeypatch.setattr(backend, "_reasoning_parser", None, raising=False)

    result = extract_from_text(
        text="document",
        text_id="test",
        prompt_template={"user_message": "{document}", "document_placeholder": "document"},
        use_guided_decoding=False,
        llm=backend,
    )

    usage: dict[str, Any] = {"completion_tokens": 5}
    if prompt_token_ids is not None:
        usage.update(prompt_tokens=len(prompt_token_ids), total_tokens=len(prompt_token_ids) + 5)
    if num_cached_tokens is not None:
        usage["prompt_tokens_details"] = {"cached_tokens": num_cached_tokens}
    assert result.backend_metadata == {"usage": usage}
    assert json.loads(json.dumps(result))["backend_metadata"] == {"usage": usage}
    assert result.structured == {}
    assert result.errors == []
