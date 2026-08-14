from typing import Literal, TypeAlias
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class CitationSource(BaseModel):
    document_id: str = Field(min_length=1, max_length=200)
    document_version: str = Field(min_length=1, max_length=200)
    chunk_id: str = Field(min_length=1, max_length=200)
    filename: str = Field(min_length=1, max_length=500)
    url: AnyHttpUrl | None = None


class CitationLocation(BaseModel):
    page: int = Field(ge=1)
    page_label: str | None = None
    total_pages: int | None = None
    start_index: int = Field(ge=0)
    end_index: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "CitationLocation":
        if self.end_index < self.start_index:
            raise ValueError("citation end_index must be greater than start_index")
        return self


class Citation(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    label: str = Field(pattern=r"^S\d+$", max_length=20)
    source: CitationSource
    location: CitationLocation
    excerpt: str = Field(min_length=1, max_length=1_000)


class RetrievalStatusChanged(BaseModel):
    phase: Literal["retrieval"] = "retrieval"
    state: Literal["active", "complete", "error"]
    label: str


class CitationsAvailable(BaseModel):
    citations: list[Citation]


class TextDelta(BaseModel):
    text: str


class ConversationStarted(BaseModel):
    conversation_id: UUID
    title: str
    assistant_message_id: str
    request_id: str


ChatEvent: TypeAlias = (
    ConversationStarted | RetrievalStatusChanged | CitationsAvailable | TextDelta
)
