import logging
from typing import Any

from llama_index.core.base.llms.types import ChatResponse, MessageRole
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
from vllm import LLM as VllmLLM
from vllm import SamplingParams
from vllm.entrypoints.chat_utils import (
    ChatCompletionMessageParam,
    CustomChatCompletionMessageParam,
)
from vllm.entrypoints.harmony_utils import parse_chat_output
from vllm.reasoning import ReasoningParser
from vllm.reasoning.gptoss_reasoning_parser import GptOssReasoningParser
from vllm.sampling_params import StructuredOutputsParams
from vllm.v1.structured_output import StructuredOutputManager

from kibad_llm.llms.base import (
    LLM,
    EmptyReasoningError,
    ReasoningExtractionError,
    SimpleChatMessage,
)

logger = logging.getLogger(__name__)

# vLLM LLM.chat has these kwargs (non-sampling). Everything else we treat as SamplingParams kwargs.
# Source: https://docs.vllm.ai/en/v0.11.2/api/vllm/entrypoints/llm/#vllm.entrypoints.llm.LLM.chat
_VLLM_CHAT_KWARGS = {
    "use_tqdm",
    "lora_request",
    "chat_template",
    "chat_template_content_format",
    "add_generation_prompt",
    "continue_final_message",
    "tools",
    "chat_template_kwargs",
    "mm_processor_kwargs",
}


def _chat_message_to_vllm_param(m: SimpleChatMessage) -> ChatCompletionMessageParam:
    msg: CustomChatCompletionMessageParam = {"role": m.role.value, "content": m.content}
    return msg


class VllmInProcess(LLM):
    """
    In-process vLLM backend using vllm.LLM.chat() so the model's chat template
    is applied automatically.

    Supports guided decoding via StructuredOutputsParams(json=...).
    Splits Harmony reasoning/final via vLLM's parse_chat_output(token_ids).
    """

    def __init__(
        self,
        *,
        model: str,
        vllm_kwargs: dict[str, Any] | None = None,
        # for compatibility with other LlamaIndex LLMs (but directly supported kwargs take precedence)
        additional_kwargs: dict[str, Any] | None = None,
        **default_request_kwargs: Any,
    ) -> None:
        self._llm = VllmLLM(model=model, **(vllm_kwargs or {}))
        self._default_request_kwargs: dict[str, Any] = additional_kwargs or {}
        self._default_request_kwargs.update(default_request_kwargs)

        self._structured_output_manager = StructuredOutputManager(
            vllm_config=self._llm.llm_engine.vllm_config
        )

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs: Any,
    ) -> ChatResponse:
        convo = [_chat_message_to_vllm_param(m) for m in messages]

        sampling_kwargs = {**self._default_request_kwargs, **request_kwargs}

        # pull out vLLM chat() kwargs; everything else goes into SamplingParams
        chat_kwargs: dict[str, Any] = {"use_tqdm": False}
        for k in list(sampling_kwargs.keys()):
            if k in _VLLM_CHAT_KWARGS:
                chat_kwargs[k] = sampling_kwargs.pop(k)

        if json_schema is not None:
            sampling_kwargs["structured_outputs"] = StructuredOutputsParams(json=json_schema)

        sampling_params = SamplingParams(**sampling_kwargs)
        req_outputs = self._llm.chat(convo, sampling_params=sampling_params, **chat_kwargs)
        # take the first output (we only sent one conversation) and first generation
        out = req_outputs[0].outputs[0]

        # If a reasoning parser is set, we assume that the model's output
        # includes reasoning that we want to extract.
        reasoner: ReasoningParser | None = self._structured_output_manager.reasoner
        if reasoner is not None:
            logger.warning(f"Using reasoning parser: {reasoner}")

            # TODO: use reasoner directly to extract reasoning/content?
            if isinstance(reasoner, GptOssReasoningParser):
                # Split Harmony output into reasoning + final (final is what we want to JSON-parse).
                reasoning, content, _is_tool_call = parse_chat_output(out.token_ids)
            else:
                raise NotImplementedError(
                    f"Reasoning parser {type(reasoner)} not supported in VllmInProcess."
                )
        else:
            reasoning = None
            content = out.text

        msg = LlamaIndexChatMessage(role=MessageRole.ASSISTANT, content=content)

        if reasoning is not None:
            msg.additional_kwargs["reasoning"] = reasoning

        return ChatResponse(message=msg, raw=req_outputs)

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str:
        """Extract reasoning from a chat response."""

        reasoning = response.message.additional_kwargs.get("reasoning")
        if not isinstance(reasoning, str):
            raise ReasoningExtractionError("Could not extract reasoning from chat response.")
        if not reasoning.strip():
            raise EmptyReasoningError("Extracted reasoning is empty.")
        return reasoning
