from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.llms.vllm import Vllm as LlamaIndexVllm
from vllm.entrypoints.harmony_utils import parse_chat_output  # vllm v0.11.x
from vllm.sampling_params import StructuredOutputsParams

from kibad_llm.llms.base import (
    LLM,
    ChatMessageExtractionError,
    MissingRawChatResponseError,
    ReasoningExtractionError,
)
from kibad_llm.utils.log import warn_once

# use this import for v0.12.x of vLLM:
# from vllm.entrypoints.openai.parser.harmony_utils import parse_chat_output


def _extract_generated_token_ids(raw: Any) -> Sequence[int]:
    """
    LlamaIndex's Vllm wrapper typically stores a vLLM RequestOutput (or a list of them)
    in ChatResponse.raw. We want raw.outputs[0].token_ids (generated output tokens).
    """
    if raw is None:
        raise MissingRawChatResponseError("ChatResponse is missing raw attribute.")

    # Some wrappers return a list[RequestOutput]
    if isinstance(raw, list):
        if not raw:
            raise ChatMessageExtractionError("ChatResponse.raw is an empty list.")
        raw0 = raw[0]
    else:
        raw0 = raw

    try:
        # vLLM RequestOutput -> list[CompletionOutput] in .outputs
        return raw0.outputs[0].token_ids
    except Exception as e:
        raise ChatMessageExtractionError(
            f"Could not extract token_ids from ChatResponse.raw: {e!r}"
        ) from e


class VllmWithHarmonyParsing(LLM):
    def __init__(self, *args, **kwargs) -> None:
        self.model = LlamaIndexVllm(*args, **kwargs)

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

        response = self.model.chat(messages, **request_kwargs)

        # --- Harmony split using vLLM's own parser (token-based, robust) ---
        token_ids = _extract_generated_token_ids(response.raw)
        reasoning, final, _is_tool_call = parse_chat_output(token_ids)

        # Normalize: put ONLY final into message.content (so json.loads works),
        # stash reasoning in additional_kwargs (your extractor can read it from there).
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
