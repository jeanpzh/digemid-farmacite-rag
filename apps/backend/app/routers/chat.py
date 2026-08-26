from __future__ import annotations

from app.adapters.vercel_request import to_langchain_messages
from app.dependencies.providers import get_chat_service
from app.schemas.conversation import ChatRequest
from app.schemas.rag_stream import STREAM_HEADERS, STREAM_MEDIA_TYPE
from app.services.chat import ChatService
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langsmith import traceable
from slowapi import Limiter


router = APIRouter(prefix="/chat", tags=["chat"])
def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip, headers_enabled=True, retry_after="integer")


@router.post("", summary="Chat with the RAG model")
@limiter.limit("10/minute")
async def chat_with_rag_model(
    request: Request,
    chat_request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    return StreamingResponse(
        _stream_events(chat_service.stream(to_langchain_messages(chat_request.messages))),
        media_type=STREAM_MEDIA_TYPE,
        headers=STREAM_HEADERS,
    )


@traceable(
    name="rag_request",
    run_type="chain",
    tags=["rag", "digemid"],
    reduce_fn=lambda chunks: {"chunk_count": len(chunks)},
)
async def _stream_events(events):
    from app.adapters.vercel_ai_stream import VercelAIStream

    async for chunk in VercelAIStream(events).stream():
        yield chunk
