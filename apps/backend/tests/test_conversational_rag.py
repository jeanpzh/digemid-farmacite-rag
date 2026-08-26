import asyncio

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from app.schemas.chat_events import (
    CitationsAvailable,
    RetrievalStatusChanged,
    TextDelta,
)

from app.services.context_builder import ContextBuilder
from app.services.chat import ChatService, format_history


def test_format_history_keeps_recent_messages_with_roles():
    messages = [
        HumanMessage(content=f"old {index}") for index in range(2)
    ] + [
        AIMessage(content="previous answer"),
        HumanMessage(content="follow-up question"),
    ]

    history = format_history(messages)

    assert history == (
        "Usuario: old 0\n"
        "Usuario: old 1\n"
        "Asistente: previous answer\n"
        "Usuario: follow-up question"
    )


def test_format_history_removes_previous_assistant_citation_markers():
    history = format_history(
        [
            HumanMessage(content="¿Qué dice la norma?"),
            AIMessage(content="La norma indica [S1]."),
        ]
    )

    assert history == "Usuario: ¿Qué dice la norma?\nAsistente: La norma indica ."


def test_context_builder_formats_source_identifiers_and_metadata():
    sources = ContextBuilder().build(
        [
            Document(
                page_content="DIGEMID supervisa medicamentos.",
                metadata={"filename": "norma.pdf", "page": 1},
            )
        ]
    )

    assert sources == (
        "[S1]\n"
        "chunk_id: unknown\n"
        "document_id: unknown\n"
        "document_version: unknown\n"
        "filename: norma.pdf\n"
        "source_url: unknown\n"
        "page: 1\n"
        "page_label: unknown\n"
        "start_index: unknown\n"
        "end_index: unknown\n"
        "content: DIGEMID supervisa medicamentos."
    )


def test_chat_service_uses_history_for_queries_and_answers():
    captured = {}

    class FakeRetriever:
        async def ainvoke(self, query, *, history=""):
            captured["retriever_input"] = (query, history)
            return [Document(page_content="fuente", metadata={"filename": "fuente.pdf"})]

    class FakeContextBuilder:
        def build(self, documents):
            return ""

    class FakeResponseGenerator:
        async def stream(self, **kwargs):
            captured["answer_input"] = kwargs
            yield "respuesta"

    service = ChatService(
        document_retriever=FakeRetriever(),
        context_formatter=FakeContextBuilder(),
        answer_streamer=FakeResponseGenerator(),
    )
    messages = [
        HumanMessage(content="¿Qué es DIGEMID?"),
        AIMessage(content="Es una autoridad sanitaria."),
        HumanMessage(content="¿Cuáles son sus funciones?"),
    ]

    chunks = asyncio.run(_collect(service.stream(messages)))

    assert chunks[-1] == TextDelta(text="respuesta")
    assert captured["retriever_input"] == (
        "¿Cuáles son sus funciones?",
        "Usuario: ¿Qué es DIGEMID?\nAsistente: Es una autoridad sanitaria.",
    )
    assert captured["answer_input"] == {
        "question": "¿Cuáles son sus funciones?",
        "history": "Usuario: ¿Qué es DIGEMID?\nAsistente: Es una autoridad sanitaria.",
        "sources": "",
    }
    assert isinstance(chunks[0], RetrievalStatusChanged)


def test_chat_service_emits_status_and_citations_before_answer():
    class FakeQueryGenerator:
        async def generate_queries(self, question, history=""):
            return []

    class FakeRetriever:
        async def ainvoke(self, query, *, history=""):
            return [
                Document(
                    id="chunk-1",
                    page_content="Fuente verificable.",
                    metadata={"filename": "fuente.pdf", "page": 2, "start_index": 10},
                )
            ]

    class FakeContextBuilder:
        def build(self, documents):
            return "contexto"

    class FakeResponseGenerator:
        async def stream(self, **kwargs):
            yield "respuesta"

    service = ChatService(
        document_retriever=FakeRetriever(),
        context_formatter=FakeContextBuilder(),
        answer_streamer=FakeResponseGenerator(),
    )

    chunks = asyncio.run(_collect(service.stream([HumanMessage(content="pregunta")])) )

    assert isinstance(chunks[0], RetrievalStatusChanged)
    assert isinstance(chunks[1], RetrievalStatusChanged)
    assert isinstance(chunks[2], CitationsAvailable)
    assert chunks[2].citations[0].source.chunk_id == "chunk-1"
    assert chunks[2].citations[0].label == "S1"
    assert chunks[2].citations[0].source.filename == "fuente.pdf"
    assert chunks[2].citations[0].location.page == 3
    assert chunks[2].citations[0].location.start_index == 10
    assert chunks[2].citations[0].location.end_index == 29


def test_chat_service_returns_deterministic_answer_when_retrieval_is_empty():
    class FakeQueryGenerator:
        async def generate_queries(self, question, history=""):
            return []

    class FakeRetriever:
        async def ainvoke(self, query, *, history=""):
            return []

    class FailingContextBuilder:
        def build(self, documents):
            raise AssertionError("context should not be built without documents")

    class FailingResponseGenerator:
        async def stream(self, **kwargs):
            raise AssertionError("model should not be called without documents")
            yield "unreachable"

    service = ChatService(
        document_retriever=FakeRetriever(),
        context_formatter=FailingContextBuilder(),
        answer_streamer=FailingResponseGenerator(),
    )

    chunks = asyncio.run(
        _collect(service.stream([HumanMessage(content="pregunta")]))
    )

    assert isinstance(chunks[1], RetrievalStatusChanged)
    assert chunks[1].label == "Sin evidencia suficiente"
    assert not any(isinstance(chunk, CitationsAvailable) for chunk in chunks)
    assert chunks[-1] == TextDelta(
        text="No encontré evidencia suficiente en las fuentes oficiales para responder esta consulta."
    )


def test_chat_service_does_not_build_context_without_documents():
    class FakeRetriever:
        async def ainvoke(self, query, *, history=""):
            return []

    class FailingContextBuilder:
        def build(self, documents):
            raise AssertionError("context should not be built without evidence")

    class FailingResponseGenerator:
        async def stream(self, **kwargs):
            raise AssertionError("model should not be called without evidence")
            yield "unreachable"

    service = ChatService(
        document_retriever=FakeRetriever(),
        context_formatter=FailingContextBuilder(),
        answer_streamer=FailingResponseGenerator(),
    )

    chunks = asyncio.run(_collect(service.stream([HumanMessage(content="pregunta")])) )

    assert chunks[1] == RetrievalStatusChanged(
        phase="retrieval", state="complete", label="Sin evidencia suficiente"
    )
    assert not any(isinstance(chunk, CitationsAvailable) for chunk in chunks)


async def _collect(stream):
    return [chunk async for chunk in stream]
