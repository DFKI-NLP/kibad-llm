from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from llama_index.core.base.llms.types import ChatResponse, MessageRole
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage

from kibad_llm.llms.base import LLM, EmptyReasoningError, ReasoningExtractionError, SimpleChatMessage

FIXTURE_FORMAT_VERSION = 1


class MockLLM(LLM):
    """Test backend that replays hashed chat fixtures and can refresh them from a real backend.

    This is intended for integration tests that should exercise the extractor pipeline without
    requiring a live LLM server on every run. Each request is normalized and hashed; the hash is
    used as the fixture filename. When ``write_fixture_data`` is enabled, the wrapped backend is
    called and the request/response snapshot is persisted. Otherwise, the stored fixture is replayed.
    """

    def __init__(
        self,
        backend: LLM,
        fixture_dir: str,
        write_fixture_data: bool = False,
        backend_name: str | None = None,
    ) -> None:
        self.backend = backend
        self.fixture_dir = Path(fixture_dir)
        self.write_fixture_data = write_fixture_data
        self.backend_name = backend_name or type(backend).__name__

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs,
    ) -> ChatResponse:
        request_snapshot = self._build_request_snapshot(
            messages=messages,
            json_schema=json_schema,
            request_kwargs=request_kwargs,
        )
        fixture_hash = self._hash_request_snapshot(request_snapshot)
        fixture_path = self.fixture_dir / f"{fixture_hash}.json"

        if self.write_fixture_data:
            self.fixture_dir.mkdir(parents=True, exist_ok=True)
            try:
                response = self.backend.call_llm_chat_with_guided_decoding(
                    messages=messages,
                    json_schema=json_schema,
                    **request_kwargs,
                )
            except Exception as e:
                self._write_fixture(
                    fixture_path=fixture_path,
                    fixture_hash=fixture_hash,
                    request_snapshot=request_snapshot,
                    response_snapshot=None,
                    error_snapshot=self._serialize_exception(e),
                )
                raise

            self._write_fixture(
                fixture_path=fixture_path,
                fixture_hash=fixture_hash,
                request_snapshot=request_snapshot,
                response_snapshot=self._serialize_response(response),
                error_snapshot=None,
            )
            return response

        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Missing MockLLM fixture: {fixture_path}. "
                "Set WRITE_FIXTURE_DATA=True and rerun the tests with a reachable backend to create it."
            )

        with open(fixture_path) as f:
            fixture_data = json.load(f)

        error_snapshot = fixture_data.get("error")
        if error_snapshot is not None:
            raise self._deserialize_exception(error_snapshot)

        response_snapshot = fixture_data.get("response")
        if response_snapshot is None:
            raise ValueError(f"Fixture {fixture_path} has neither a response nor an error.")
        return self._deserialize_response(response_snapshot)

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str | None:
        try:
            delegated = self.backend.get_reasoning_from_chat_response(response)
            if delegated is not None:
                return delegated
        except Exception:
            pass

        raw_msg = self.get_raw_message_from_chat_response(response)
        result = getattr(raw_msg, "reasoning", None) or getattr(raw_msg, "reasoning_content", None)
        if not isinstance(result, str):
            raise ReasoningExtractionError("Could not extract reasoning from chat response.")
        if not result.strip():
            raise EmptyReasoningError("Extracted reasoning is empty.")
        return result

    def _build_request_snapshot(
        self,
        *,
        messages: list[SimpleChatMessage],
        json_schema: dict[str, Any] | None,
        request_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "fixture_format_version": FIXTURE_FORMAT_VERSION,
            "backend_name": self.backend_name,
            "backend_type": f"{type(self.backend).__module__}.{type(self.backend).__qualname__}",
            "messages": [
                {
                    "role": message.role.value if isinstance(message.role, Enum) else str(message.role),
                    "content": message.content,
                }
                for message in messages
            ],
            "json_schema": self._normalize_jsonable(json_schema),
            "request_kwargs": self._normalize_jsonable(request_kwargs),
        }

    def _hash_request_snapshot(self, request_snapshot: dict[str, Any]) -> str:
        serialized = json.dumps(
            request_snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _write_fixture(
        self,
        *,
        fixture_path: Path,
        fixture_hash: str,
        request_snapshot: dict[str, Any],
        response_snapshot: dict[str, Any] | None,
        error_snapshot: dict[str, Any] | None,
    ) -> None:
        payload = {
            "fixture_format_version": FIXTURE_FORMAT_VERSION,
            "fixture_hash": fixture_hash,
            "request": request_snapshot,
            "response": response_snapshot,
            "error": error_snapshot,
        }
        with open(fixture_path, "w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _serialize_response(self, response: ChatResponse) -> dict[str, Any]:
        raw_message = None
        try:
            raw_message = self.get_raw_message_from_chat_response(response)
        except Exception:
            raw_message = None

        return {
            "message": {
                "role": MessageRole.ASSISTANT.value,
                "content": response.message.content,
            },
            "raw_message": {
                "reasoning": getattr(raw_message, "reasoning", None),
                "reasoning_content": getattr(raw_message, "reasoning_content", None),
            },
        }

    def _deserialize_response(self, response_snapshot: dict[str, Any]) -> ChatResponse:
        message_snapshot = response_snapshot.get("message") or {}
        raw_message_snapshot = response_snapshot.get("raw_message") or {}

        raw_message = SimpleNamespace(
            reasoning=raw_message_snapshot.get("reasoning"),
            reasoning_content=raw_message_snapshot.get("reasoning_content"),
        )
        raw = SimpleNamespace(choices=[SimpleNamespace(message=raw_message)])
        return ChatResponse(
            message=LlamaIndexChatMessage(
                role=MessageRole(message_snapshot.get("role", MessageRole.ASSISTANT.value)),
                content=message_snapshot.get("content"),
            ),
            raw=raw,
        )

    def _serialize_exception(self, e: Exception) -> dict[str, Any]:
        return {
            "module": type(e).__module__,
            "qualname": type(e).__qualname__,
            "message": str(e),
        }

    def _deserialize_exception(self, error_snapshot: dict[str, Any]) -> Exception:
        module_name = error_snapshot.get("module")
        qualname = error_snapshot.get("qualname")
        message = error_snapshot.get("message", "")

        exc_cls: type[Exception] | None = None
        if isinstance(module_name, str) and isinstance(qualname, str):
            try:
                module = importlib.import_module(module_name)
                obj: Any = module
                for attr in qualname.split("."):
                    obj = getattr(obj, attr)
                if isinstance(obj, type) and issubclass(obj, Exception):
                    exc_cls = obj
            except (ImportError, AttributeError, TypeError):
                exc_cls = None

        if exc_cls is None:
            return ValueError(f"{qualname or 'Exception'}: {message}")
        exception_factory = cast(type[Exception], exc_cls)
        exception = exception_factory(message)
        return exception

    def _normalize_jsonable(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(k): self._normalize_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._normalize_jsonable(v) for v in value]
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Path):
            return str(value)
        return value


