from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


IndexingRunStatus = Literal["running", "paused", "completed", "failed", "cancelled"]
IndexingMode = Literal["all", "pending"]
DocumentIndexingStatus = Literal["pending", "processing", "indexed", "failed"]


class IndexingRunStartRequest(BaseModel):
    collection: str = Field(default="digemid", min_length=1, max_length=120)
    mode: IndexingMode = "pending"


class IndexingDocumentRead(BaseModel):
    id: int
    filename: str
    source_url: str | None = None
    status: DocumentIndexingStatus
    stage: str
    progress: int = Field(ge=0, le=100)
    last_error: str | None = None


class IndexingRunRead(BaseModel):
    run_id: UUID
    collection: str
    mode: IndexingMode
    status: IndexingRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    completed: int = 0
    total: int = 0
    progress: int = Field(default=0, ge=0, le=100)
    stage: str = "Esperando una acción"
    elapsed_seconds: int = Field(default=0, ge=0)
    documents: list[IndexingDocumentRead] = Field(default_factory=list)
