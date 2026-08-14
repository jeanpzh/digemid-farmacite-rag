from __future__ import annotations

import asyncio
from uuid import UUID

from app.adapters.vercel_request import to_langchain_messages
from app.dependencies.providers import get_chat_service
from app.schemas.conversation import ChatRequest
from app.schemas.rag_stream import STREAM_HEADERS, STREAM_MEDIA_TYPE
from app.services.chat import ChatService
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langsmith import traceable
from sqlalchemy.exc import IntegrityError


router = APIRouter(prefix="/chat", tags=["chat"])


@traceable(name="rag-query-1", tags=["rag", "digemid"])
@router.post("", summary="Chat with the RAG model")
async def chat_with_rag_model(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    return StreamingResponse(
        _stream_events(chat_service.stream(to_langchain_messages(request.messages))),
        media_type=STREAM_MEDIA_TYPE,
        headers=STREAM_HEADERS,
    )


async def _stream_events(events):
    from app.adapters.vercel_ai_stream import VercelAIStream

    async for chunk in VercelAIStream(events).stream():
        yield chunk
