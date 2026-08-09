from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("doc_hash", "collection", name="documents_doc_hash_collection_key"),
        UniqueConstraint("storage_key", "collection", name="documents_collection_storage_key"),
        Index(
            "documents_collection_status_idx",
            "collection",
            "status",
            "lease_until",
            "created_at",
        ),
        {"schema": "rag"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    doc_hash: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    retries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    collection: Mapped[str] = mapped_column(String, nullable=False, default="default")
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(Text)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
