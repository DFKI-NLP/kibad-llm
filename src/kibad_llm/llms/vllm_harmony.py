from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from llama_index.core.base.llms.generic_utils import (
    completion_response_to_chat_response,
)
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    CompletionResponse,
)
from llama_index.llms.vllm import Vllm as LlamaIndexVllm
from vllm.sampling_params import StructuredOutputsParams

from kibad_llm.llms.base import LLM, ReasoningExtractionError
from kibad_llm.utils.log import warn_once


def _parse_chat_output(token_ids: Sequence[int]) -> tuple[str | None, str | None, bool]:
    # vLLM 0.11.2 location
    from vllm.entrypoints.harmony_utils import parse_chat_output

    return parse_chat_output(token_ids)


class _LlamaIndexVllmWithRaw(LlamaIndexVllm):
    """Same as LlamaIndex Vllm, but keeps vLLM RequestOutput in CompletionResponse.raw."""

    def complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        kwargs = kwargs if kwargs else {}
        params = {**self._model_kwargs, **kwargs}

        from vllm import SamplingParams

        sampling_params = SamplingParams(**params)
        outputs = self._client.generate([prompt], sampling_params)

        req_out = outputs[0]  # vLLM RequestOutput
        comp_out = req_out.outputs[0]  # vLLM CompletionOutput
        return CompletionResponse(text=comp_out.text, raw=req_out)


class VllmWithHarmonyParsing(LLM):
    def __init__(self, *args, **kwargs) -> None:
        self.model = _LlamaIndexVllmWithRaw(*args, **kwargs)

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs,
    ) -> ChatResponse:
        if json_schema is not None:
            if "structured_outputs" in request_kwargs:
                warn_once(
                    f'Overwriting existing "structured_outputs": {request_kwargs["structured_outputs"]} '
                    "in request_parameters with provided json schema for guided decoding."
                )
            request_kwargs["structured_outputs"] = StructuredOutputsParams(json=json_schema)

        # Use the normal LlamaIndex path, but now complete() preserves raw.
        prompt = self.model.messages_to_prompt(messages)
        completion = self.model.complete(prompt, **request_kwargs)
        response = completion_response_to_chat_response(completion)

        # Harmony split using vLLM's own parser (token-based)
        req_out = response.raw  # vLLM RequestOutput
        token_ids = req_out.outputs[0].token_ids
        reasoning, final, _is_tool_call = _parse_chat_output(token_ids)

        if final is not None:
            response.message.content = final
        if reasoning is not None:
            response.additional_kwargs["reasoning"] = reasoning

        return response

    @staticmethod
    def get_reasoning_from_chat_response(response: ChatResponse) -> str:
        reasoning = response.additional_kwargs.get(
            "reasoning"
        ) or response.message.additional_kwargs.get("reasoning")
        if not reasoning:
            raise ReasoningExtractionError("No reasoning found in ChatResponse additional_kwargs.")
        return reasoning
