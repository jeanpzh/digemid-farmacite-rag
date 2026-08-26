from collections.abc import AsyncIterator, Sequence
import re
from typing import Protocol, runtime_checkable

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage

from app.schemas.chat_events import (
    ChatEvent,
    CitationsAvailable,
    RetrievalStatusChanged,
    TextDelta,
)
from app.services.citations import build_citations
from app.services.observability import stream_with_ttft

MAX_HISTORY_MESSAGES = 6


@runtime_checkable
class DocumentRetriever(Protocol):
    async def ainvoke(self, query: str, *, history: str = "") -> list[Document]: ...


@runtime_checkable
class ContextFormatter(Protocol):
    def build(self, documents: list[Document]) -> str: ...


@runtime_checkable
class AnswerStreamer(Protocol):
    def stream(
        self,
        *,
        question: str,
        history: str,
        sources: str,
    ) -> AsyncIterator[str]: ...


def format_history(messages: Sequence[BaseMessage]) -> str:
    history = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        content = str(message.content).strip()
        if not content:
            continue
        if message.type == "ai":
            content = re.sub(r"\[S\d+\]", "", content).strip()
            if not content:
                continue
        role = {
            "human": "Usuario",
            "ai": "Asistente",
            "system": "Sistema",
        }.get(message.type, "Asistente")
        history.append(f"{role}: {content}")
    return "\n".join(history)

class ChatService:
    def __init__(
        self,
        document_retriever: DocumentRetriever,
        context_formatter: ContextFormatter,
        answer_streamer: AnswerStreamer,
    ):
        self._document_retriever = document_retriever
        self._context_formatter = context_formatter
        self._answer_streamer = answer_streamer

    async def stream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[ChatEvent]:
        question = str(messages[-1].content) if messages else ""
        history = format_history(messages[:-1])

        yield RetrievalStatusChanged(
            phase="retrieval",
            state="active",
            label="Buscando fuentes relevantes",
        )

        try:
            documents = await self._document_retriever.ainvoke(
                question,
                history=history,
            )
        except Exception:
            yield RetrievalStatusChanged(
                phase="retrieval",
                state="error",
                label="No se pudieron recuperar fuentes",
            )
            raise

        yield RetrievalStatusChanged(
            phase="retrieval",
            state="complete",
            label=(
                f"Se encontraron {len(documents)} fuentes"
                if documents
                else "Sin evidencia suficiente"
            ),
        )

        if not documents:
            yield TextDelta(
                text="No encontré evidencia suficiente en las fuentes oficiales para responder esta consulta."
            )
            return

        yield CitationsAvailable(citations=build_citations(documents))

        context = self._context_formatter.build(documents)
        answer_stream = self._answer_streamer.stream(
            question=question,
            history=history,
            sources=context,
        )
        async for chunk in stream_with_ttft(answer_stream):
            if chunk:
                yield TextDelta(text=str(chunk))
