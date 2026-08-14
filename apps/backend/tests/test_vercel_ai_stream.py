import asyncio
import json

from app.adapters.vercel_ai_stream import VercelAIStream
from app.schemas.chat_events import (
    CitationsAvailable,
    Citation,
    CitationLocation,
    CitationSource,
    ConversationStarted,
    RetrievalStatusChanged,
    TextDelta,
)


async def _events():
    yield ConversationStarted(
        conversation_id="7f8f7a54-1fd4-4b35-a6ac-d5f3ab6e13f8",
        title="pregunta",
        assistant_message_id="assistant-1",
        request_id="request-1",
    )
    yield RetrievalStatusChanged(
        state="complete",
        label="Se encontraron 1 fuentes",
    )
    yield CitationsAvailable(
        citations=[
            Citation(
                id="cit_1",
                label="S1",
                source=CitationSource(
                    document_id="document-1",
                    document_version="version-1",
                    chunk_id="chunk-1",
                    filename="fuente.pdf",
                ),
                location=CitationLocation(
                    page=3,
                    start_index=10,
                    end_index=29,
                ),
                excerpt="Fuente verificable.",
            )
        ]
    )
    yield TextDelta(text="respuesta")


def test_vercel_ai_stream_maps_application_events_to_ui_stream():
    chunks = asyncio.run(_collect(VercelAIStream(_events()).stream()))

    assert _payload(chunks[0]) == {
        "type": "start",
        "messageId": "assistant-1",
        "messageMetadata": {
            "conversationId": "7f8f7a54-1fd4-4b35-a6ac-d5f3ab6e13f8",
            "requestId": "request-1",
            "title": "pregunta",
        },
    }
    assert _payload(chunks[1]) == {
        "type": "data-status",
        "data": {
            "phase": "retrieval",
            "state": "complete",
            "label": "Se encontraron 1 fuentes",
        },
        "transient": True,
    }
    assert _payload(chunks[2])["type"] == "data-citation"
    assert _payload(chunks[2])["id"] == "cit_1"
    assert _payload(chunks[2])["data"]["label"] == "S1"
    assert _payload(chunks[2])["data"]["source"]["documentId"] == "document-1"
    assert _payload(chunks[2])["data"]["source"]["chunkId"] == "chunk-1"
    assert _payload(chunks[3])["type"] == "text-start"
    assert _payload(chunks[4])["type"] == "text-delta"
    assert _payload(chunks[5])["type"] == "text-end"
    assert _payload(chunks[6]) == {"type": "finish", "finishReason": "stop"}
    assert chunks[7] == "data: [DONE]\n\n"


def test_vercel_ai_stream_does_not_open_text_part_before_text():
    async def events():
        yield ConversationStarted(
            conversation_id="7f8f7a54-1fd4-4b35-a6ac-d5f3ab6e13f8",
            title="pregunta",
            assistant_message_id="assistant-1",
            request_id="request-1",
        )
        yield RetrievalStatusChanged(state="active", label="Buscando fuentes")

    chunks = asyncio.run(_collect(VercelAIStream(events()).stream()))
    types = [_payload(chunk)["type"] for chunk in chunks[:-1]]

    assert types == ["start", "data-status", "finish"]
    assert chunks[-1] == "data: [DONE]\n\n"


def test_vercel_ai_stream_preserves_first_non_conversation_event():
    async def events():
        yield RetrievalStatusChanged(state="active", label="Buscando fuentes")

    chunks = asyncio.run(_collect(VercelAIStream(events()).stream()))

    assert [_payload(chunk)["type"] for chunk in chunks[:-1]] == [
        "start",
        "data-status",
        "finish",
    ]


def test_vercel_ai_stream_finishes_with_error_after_source_failure():
    async def events():
        yield ConversationStarted(
            conversation_id="7f8f7a54-1fd4-4b35-a6ac-d5f3ab6e13f8",
            title="pregunta",
            assistant_message_id="assistant-1",
            request_id="request-1",
        )
        yield RetrievalStatusChanged(state="active", label="Buscando fuentes")
        raise RuntimeError("retrieval failed")

    chunks = asyncio.run(_collect(VercelAIStream(events()).stream()))

    assert _payload(chunks[-2]) == {
        "type": "finish",
        "finishReason": "error",
    }
    assert chunks[-1] == "data: [DONE]\n\n"


def _payload(chunk: str) -> dict:
    return json.loads(chunk.removeprefix("data: ").strip())


async def _collect(stream):
    return [chunk async for chunk in stream]
