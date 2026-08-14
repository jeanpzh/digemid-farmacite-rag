import asyncio
import logging
from collections.abc import AsyncIterator
from uuid import uuid4

from app.schemas.chat_events import (
    ChatEvent,
    CitationsAvailable,
    ConversationStarted,
    RetrievalStatusChanged,
    TextDelta,
)
from app.schemas.rag_stream import (
    CitationEvent,
    ErrorEvent,
    FinishEvent,
    RetrievalStatus,
    RetrievalStatusEvent,
    StartEvent,
    StreamCitation,
    TextDeltaEvent,
    TextEndEvent,
    TextStartEvent,
    encode_event,
)

logger = logging.getLogger(__name__)


class VercelAIStream:
    def __init__(self, events: AsyncIterator[ChatEvent]):
        self._events = events

    async def stream(self) -> AsyncIterator[str]:
        text_id = f"text-{uuid4()}"
        text_started = False
        stream_started = False

        try:
            async for event in self._events:
                if not stream_started:
                    assistant_message_id = (
                        event.assistant_message_id
                        if isinstance(event, ConversationStarted)
                        else f"msg-{uuid4()}"
                    )
                    metadata = None
                    if isinstance(event, ConversationStarted):
                        metadata = {
                            "conversationId": str(event.conversation_id),
                            "requestId": event.request_id,
                            "title": event.title,
                        }
                    yield encode_event(
                        StartEvent(
                            messageId=assistant_message_id,
                            messageMetadata=metadata,
                        )
                    )
                    stream_started = True

                if isinstance(event, ConversationStarted):
                    continue
                if isinstance(event, RetrievalStatusChanged):
                    yield encode_event(
                        RetrievalStatusEvent(
                            data=RetrievalStatus(
                                phase=event.phase,
                                state=event.state,
                                label=event.label,
                            )
                        )
                    )
                elif isinstance(event, CitationsAvailable):
                    for citation in event.citations:
                        stream_citation = StreamCitation.model_validate(
                            citation.model_dump()
                        )
                        yield encode_event(
                            CitationEvent(
                                id=stream_citation.id,
                                data=stream_citation,
                            )
                        )
                elif isinstance(event, TextDelta):
                    if not event.text:
                        continue
                    if not text_started:
                        text_started = True
                        yield encode_event(TextStartEvent(id=text_id))
                    yield encode_event(
                        TextDeltaEvent(id=text_id, delta=event.text)
                    )
                else:
                    raise TypeError(f"Unsupported chat event: {type(event)!r}")
        except asyncio.CancelledError:
            raise
        except Exception:
            if text_started:
                yield encode_event(TextEndEvent(id=text_id))
            yield encode_event(
                ErrorEvent(errorText="No se pudo generar la respuesta.")
            )
            yield encode_event(FinishEvent(finishReason="error"))
            yield "data: [DONE]\n\n"
            return
        finally:
            close = getattr(self._events, "aclose", None)
            if close is not None:
                try:
                    await close()
                except Exception:
                    logger.exception("Failed to close chat event stream")

        if text_started:
            yield encode_event(TextEndEvent(id=text_id))
        yield encode_event(FinishEvent(finishReason="stop"))
        yield "data: [DONE]\n\n"
