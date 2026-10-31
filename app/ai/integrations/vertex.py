from collections.abc import AsyncIterator, Iterator
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI


class VertexMaaSChatOpenAI(ChatOpenAI):
    """Vertex's OpenAI-compat shim 400s on messages with no content, and tool-call turns have
    none, so they get a single space. Overrides both the buffered and streaming paths."""

    @staticmethod
    def _pad_tool_call_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
        padded: list[BaseMessage] = []
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls and not msg.content:
                msg = msg.model_copy(update={"content": " "})
            padded.append(msg)
        return padded

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return super()._generate(
            self._pad_tool_call_messages(messages), stop=stop, run_manager=run_manager, **kwargs
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return await super()._agenerate(
            self._pad_tool_call_messages(messages), stop=stop, run_manager=run_manager, **kwargs
        )

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        return super()._stream(
            self._pad_tool_call_messages(messages), stop=stop, run_manager=run_manager, **kwargs
        )

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        async for chunk in super()._astream(
            self._pad_tool_call_messages(messages), stop=stop, run_manager=run_manager, **kwargs
        ):
            yield chunk
