"""Test preservation of API token usage across the shared LLM interface."""

import copy
import json
from types import SimpleNamespace

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from openai.types import CompletionUsage
from openai.types.responses import ResponseUsage
import pytest

from kibad_llm.llms.openai import OpenAI
from kibad_llm.llms.openai_like_vllm import OpenAILikeVllm


@pytest.fixture(params=["openai", "vllm"])
def backend_and_usage(request):
    """Create API backends and their SDK usage models without making requests."""
    if request.param == "openai":
        return OpenAI(model="gpt-5", api_key="unused"), ResponseUsage(
            input_tokens=120,
            input_tokens_details={"cached_tokens": 80},
            output_tokens=30,
            output_tokens_details={"reasoning_tokens": 10},
            total_tokens=150,
        )
    return OpenAILikeVllm(model="test-model", api_key="unused"), CompletionUsage(
        prompt_tokens=120,
        prompt_tokens_details={"cached_tokens": 0},
        completion_tokens=30,
        completion_tokens_details={"reasoning_tokens": 10},
        total_tokens=150,
    )


@pytest.mark.parametrize("as_dict", [False, True])
def test_backend_metadata_preserves_usage_details(backend_and_usage, as_dict: bool) -> None:
    """Keep native fields and nested details, and return an independent JSON value."""
    backend, usage = backend_and_usage
    expected = usage.model_dump(mode="json")
    raw = {"usage": copy.deepcopy(expected)} if as_dict else SimpleNamespace(usage=usage)
    response = ChatResponse(message=ChatMessage(content="{}"), raw=raw)

    metadata = backend.get_backend_metadata_from_chat_response(response)

    assert metadata == {"usage": expected}
    assert json.loads(json.dumps(metadata)) == metadata
    assert metadata is not None
    details_key = (
        "input_tokens_details" if "input_tokens_details" in expected else "prompt_tokens_details"
    )
    metadata["usage"][details_key]["cached_tokens"] = 999
    original = raw["usage"] if isinstance(raw, dict) else usage.model_dump(mode="json")
    assert original == expected


@pytest.mark.parametrize("raw", [None, {}, {"usage": None}, SimpleNamespace()])
def test_backend_metadata_is_unavailable_without_usage(backend_and_usage, raw) -> None:
    """Do not invent zero usage for a backend that does not report it."""
    backend, _ = backend_and_usage
    response = ChatResponse(message=ChatMessage(content="{}"), raw=raw)
    assert backend.get_backend_metadata_from_chat_response(response) is None


def test_backend_metadata_rejects_malformed_usage(backend_and_usage) -> None:
    """Expose unexpected backend usage rather than silently discarding it."""
    backend, _ = backend_and_usage
    response = ChatResponse(message=ChatMessage(content="{}"), raw={"usage": "invalid"})
    with pytest.raises(TypeError, match="Unsupported token usage type"):
        backend.get_backend_metadata_from_chat_response(response)
