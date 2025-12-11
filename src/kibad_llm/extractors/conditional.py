from typing import Any

from llama_index.core.base.llms.types import ChatMessage

from .base import extract_from_text_lenient
from .union import UnionExtractor, _aggregate_structured_outputs_union


class ConditionalUnionExtractor(UnionExtractor):
    """Extractor that repeats extraction multiple times with history and aggregates results per key.
    This extractor calls the base extraction function multiple times (for each entry in overrides)
    on the same input text, passing the history of previous messages to each subsequent call.

    See UnionExtractor for accepted parameters and details about the aggregation logic.
    """

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        results = []
        history: list[ChatMessage] = []
        for override_params in self.overrides:
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
                current_kwargs["system_message"] = None
                current_kwargs["history"] = history

            current_result = extract_from_text_lenient(*args, **current_kwargs)

            # collect messages for history
            for role, content in current_result["messages_formatted"].items():
                history.append(ChatMessage(role=role, content=content))
            # append assistant response or error to history
            history.append(
                ChatMessage(
                    role="assistant",
                    content=current_result["response_content"] or current_result["error"],
                )
            )

            results.append(current_result)

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = _aggregate_structured_outputs_union(
            structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        )

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]
        return result
