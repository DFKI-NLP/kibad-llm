from __future__ import annotations

from collections.abc import Callable
from typing import Any

from llama_index.core.base.llms.types import ChatMessage, ChatResponse, MessageRole
from vllm import LLM as VllmLLM
from vllm import SamplingParams
from vllm.entrypoints.harmony_utils import parse_chat_output
from vllm.sampling_params import StructuredOutputsParams

from kibad_llm.llms.base import LLM
from kibad_llm.utils.log import warn_once


def default_messages_to_prompt(messages: list[ChatMessage]) -> str:
    # For GPT-OSS you may want to replace this with the model's real chat template.
    # LlamaIndex's ChatMessage.__str__ is "role: content". :contentReference[oaicite:6]{index=6}
    return "\n".join(str(m) for m in messages)


class VllmDirect(LLM):
    def __init__(
        self,
        *,
        model: str,
        vllm_kwargs: dict[str, Any] | None = None,
        messages_to_prompt: Callable[[list[ChatMessage]], str] | None = None,
        # default sampling kwargs:
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int = 4096,
        **extra_sampling_kwargs: Any,
    ) -> None:
        self._llm = VllmLLM(model=model, **(vllm_kwargs or {}))
        self._messages_to_prompt = messages_to_prompt or default_messages_to_prompt
        self._default_sampling = {
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            **extra_sampling_kwargs,
        }

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs: Any,
    ) -> ChatResponse:
        prompt = self._messages_to_prompt(messages)

        sampling_kwargs = dict(self._default_sampling)
        sampling_kwargs.update(request_kwargs)

        if json_schema is not None:
            if "structured_outputs" in sampling_kwargs:
                warn_once(
                    f'Overwriting existing "structured_outputs": {sampling_kwargs["structured_outputs"]} '
                    "with provided json schema."
                )
            sampling_kwargs["structured_outputs"] = StructuredOutputsParams(json=json_schema)

        sampling_params = SamplingParams(**sampling_kwargs)
        req_out = self._llm.generate([prompt], sampling_params)[0]
        comp_out = req_out.outputs[
            0
        ]  # CompletionOutput has .text and .token_ids :contentReference[oaicite:7]{index=7}

        reasoning, final, _is_tool_call = parse_chat_output(
            comp_out.token_ids
        )  # :contentReference[oaicite:8]{index=8}
        text = final if final is not None else comp_out.text

        msg = ChatMessage(
            role=MessageRole.ASSISTANT, content=text
        )  # content -> TextBlock :contentReference[oaicite:9]{index=9}

        additional_kwargs: dict[str, Any] = {}
        if reasoning is not None:
            # put it where your pipeline can find it
            msg.additional_kwargs["reasoning"] = reasoning
            additional_kwargs["reasoning"] = reasoning

        # raw can be Any|None; store the vLLM object or a trimmed dict :contentReference[oaicite:10]{index=10}
        return ChatResponse(message=msg, raw=req_out, additional_kwargs=additional_kwargs)
