from typing import Any

from llama_index.core.base.llms.types import ChatResponse
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
from llama_index.llms.openai import OpenAI as LlamaIndexOpenAI

from kibad_llm.llms.base import LLM, SimpleChatMessage
from kibad_llm.utils.log import warn_once


class OpenAI(LLM):
    """Simple wrapper around OpenAI LLMs to handle guided decoding in extractors.extract_from_text"""

    def __init__(self, *args, **kwargs) -> None:
        self.model = LlamaIndexOpenAI(*args, **kwargs)

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs,
    ) -> ChatResponse:
        if json_schema is not None:
            raise NotImplementedError(
                "Guided decoding with json_schema is not implemented for OpenAI LLMs. "
                "Please use a vLLM-based model via OpenAILikeVllm instead."
            )

        llama_index_messages = [
            LlamaIndexChatMessage(role=msg.role, content=msg.content) for msg in messages
        ]
        return self.model.chat(llama_index_messages, **request_kwargs)
