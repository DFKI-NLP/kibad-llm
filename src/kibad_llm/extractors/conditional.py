"""Conditional (multi-turn) union extractor that feeds each run's output as history.

[`ConditionalUnionExtractor`][kibad_llm.extractors.conditional.ConditionalUnionExtractor] extends [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor]
by maintaining a running conversation history: each extraction run's formatted messages and
the assistant's response are appended to the history before the next run is called, turning
the extraction into a multi-turn dialogue.  This is useful when later schema fields benefit
from the context already established in earlier turns (e.g., first extract coarse categories,
then refine details).
"""

from typing import Any

from llama_index.core.base.llms.types import MessageRole

from kibad_llm.llms.base import SimpleChatMessage

from .base import extract_from_text_lenient
from .union import UnionExtractor


class ConditionalUnionExtractor(UnionExtractor):
    """Extractor that repeats extraction multiple times with history and aggregates results per key.
    This extractor calls the base extraction function multiple times (for each entry in overrides)
    on the same input text, passing the history of previous messages to each subsequent call.

    See UnionExtractor for accepted parameters and details about the aggregation logic.
    """

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        results = []
        history: list[SimpleChatMessage] = []
        for override_name, override_params in self.overrides.items():
            # adjust kwargs:
            # 1) to return formatted messages for history
            current_kwargs = {
                **combined_kwargs,
                **override_params,
                "return_messages_formatted": True,
                "truncate_user_message_formatted": None,
            }
            # 2) if history exists, pass it and disable system message
            if len(history) > 0:
                current_kwargs["prompt_template"]["system_message"] = None
                current_kwargs["history"] = history

            current_result = extract_from_text_lenient(*args, **current_kwargs)

            # collect messages for history
            for role_str, content in current_result["messages_formatted"].items():
                role = MessageRole(role_str)
                history.append(SimpleChatMessage(role=role, content=content))
            # append assistant response or error to history
            history.append(
                SimpleChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=current_result["response_content"] or current_result["error"],
                )
            )

            results.append(current_result)

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = self.aggregator(structured_outputs)

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]
        return result
