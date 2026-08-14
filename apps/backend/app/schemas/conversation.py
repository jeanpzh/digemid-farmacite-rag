from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


MessageRole = Literal["user", "assistant"]
MessageStatus = Literal["streaming", "completed", "failed", "cancelled"]


class TextPartInput(BaseModel):
    type: Literal["text"]
    text: str = Field(max_length=20_000)


class ConversationMessageInput(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    role: MessageRole
    parts: list[TextPartInput] = Field(min_length=1, max_length=32)

    @property
    def text(self) -> str:
        return "".join(
            part.text for part in self.parts
        ).strip()


class ChatRequest(BaseModel):
    conversation_id: UUID | None = Field(default=None, alias="conversationId")
    request_id: str = Field(alias="requestId", min_length=1, max_length=200)
    messages: list[ConversationMessageInput] = Field(min_length=1, max_length=7)

    model_config = ConfigDict(populate_by_name=True)

    @property
    def message(self) -> ConversationMessageInput:
        return self.messages[-1]

    @field_validator("messages")
    @classmethod
    def validate_last_message(cls, messages: list[ConversationMessageInput]) -> list[ConversationMessageInput]:
        if messages[-1].role != "user" or not messages[-1].text:
            raise ValueError("the last message must be a non-empty user message")
        if sum(len(part.text) for part in messages[-1].parts) > 20_000:
            raise ValueError("the user message is too long")
        return messages


class ConversationMessage(BaseModel):
    id: UUID
    ui_message_id: str = Field(alias="uiMessageId")
    position: int
    role: MessageRole
    status: MessageStatus
    parts: list[dict[str, Any]]
    content_text: str = Field(alias="contentText")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    message_count: int = Field(alias="messageCount")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage]


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None = Field(default=None, alias="nextCursor")

    model_config = ConfigDict(populate_by_name=True)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, title: str) -> str:
        normalized = " ".join(title.split())
        if not normalized:
            raise ValueError("title must not be empty")
        return normalized


def encode_cursor(updated_at: datetime, conversation_id: UUID) -> str:
    payload = json.dumps(
        {"updatedAt": updated_at.isoformat(), "id": str(conversation_id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    padding = "=" * (-len(cursor) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        return datetime.fromisoformat(payload["updatedAt"]), UUID(payload["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid cursor") from exc
