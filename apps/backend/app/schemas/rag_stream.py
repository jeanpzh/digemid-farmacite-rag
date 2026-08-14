"""Vercel AI SDK UI message stream wire models and SSE encoding."""

import json
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

STREAM_MEDIA_TYPE = "text/event-stream"
STREAM_HEADERS = {
    "content-type": STREAM_MEDIA_TYPE,
    "cache-control": "no-cache, no-transform",
    "connection": "keep-alive",
    "content-encoding": "none",
    "x-accel-buffering": "no",
    "x-vercel-ai-ui-message-stream": "v1",
}


class StartEvent(BaseModel):
    type: Literal["start"] = "start"
    message_id: str = Field(alias="messageId")
    message_metadata: dict[str, str] | None = Field(
        default=None,
        alias="messageMetadata",
    )

    model_config = ConfigDict(populate_by_name=True)


class RetrievalStatus(BaseModel):
    phase: Literal["retrieval"] = "retrieval"
    state: Literal["active", "complete", "error"]
    label: str


class RetrievalStatusEvent(BaseModel):
    type: Literal["data-status"] = "data-status"
    data: RetrievalStatus
    transient: bool = True


class CitationLocation(BaseModel):
    page: int = Field(ge=1)
    page_label: str | None = Field(default=None, alias="pageLabel")
    total_pages: int | None = Field(default=None, alias="totalPages")
    start_index: int = Field(alias="startIndex", ge=0)
    end_index: int = Field(alias="endIndex", ge=0)

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_range(self) -> "CitationLocation":
        if self.end_index < self.start_index:
            raise ValueError("citation end_index must be greater than start_index")
        return self


class CitationSource(BaseModel):
    document_id: str = Field(alias="documentId")
    document_version: str = Field(alias="documentVersion")
    chunk_id: str = Field(alias="chunkId")
    filename: str
    url: AnyHttpUrl | None = None

    model_config = ConfigDict(populate_by_name=True)


class StreamCitation(BaseModel):
    id: str
    label: str
    source: CitationSource
    location: CitationLocation
    excerpt: str


class CitationEvent(BaseModel):
    type: Literal["data-citation"] = "data-citation"
    id: str
    data: StreamCitation


class TextStartEvent(BaseModel):
    type: Literal["text-start"] = "text-start"
    id: str


class TextDeltaEvent(BaseModel):
    type: Literal["text-delta"] = "text-delta"
    id: str
    delta: str


class TextEndEvent(BaseModel):
    type: Literal["text-end"] = "text-end"
    id: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    error_text: str = Field(alias="errorText")

    model_config = ConfigDict(populate_by_name=True)


class FinishEvent(BaseModel):
    type: Literal["finish"] = "finish"
    finish_reason: Literal[
        "stop", "length", "content-filter", "tool-calls", "error", "other"
    ] = Field(default="stop", alias="finishReason")

    model_config = ConfigDict(populate_by_name=True)


StreamEvent = (
    StartEvent
    | RetrievalStatusEvent
    | CitationEvent
    | TextStartEvent
    | TextDeltaEvent
    | TextEndEvent
    | ErrorEvent
    | FinishEvent
)


def encode_event(event: StreamEvent) -> str:
    payload = json.dumps(
        event.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
    )
    return f"data: {payload}\n\n"
