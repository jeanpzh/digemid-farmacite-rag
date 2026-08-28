from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class IndexRun(Base):
    __tablename__ = "index_runs"
    __table_args__ = {"schema": "rag"}

    run_id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    collection: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, nullable=False)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
