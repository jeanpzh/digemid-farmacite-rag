import os
import socket
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.models.document import Document

LEASE_DURATION = timedelta(minutes=15)
MAX_RETRIES = 3


def staged_collection(collection: str) -> str:
    return f"{collection}:review"


def claim_document(
    session: Session, collection: str, *, uploads_only: bool = False
) -> Document | None:
    now = datetime.now(timezone.utc)
    query = select(Document).where(
        Document.collection == collection,
        Document.publication != "archived",
        or_(
            Document.status == "pending",
            (Document.status == "processing") & (Document.lease_until < now),
            (Document.status == "failed") & (Document.origin == "corpus") & (Document.retries < MAX_RETRIES),
        ),
    )
    if uploads_only:
        query = query.where(Document.queued_from_ui.is_(True))
    document = session.scalars(
        query.order_by(Document.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    ).first()
    if document is None:
        return None

    document.status = "processing"
    document.lease_owner = f"{socket.gethostname()}:{os.getpid()}:{uuid4()}"
    document.lease_until = now + LEASE_DURATION
    document.retries += 1
    document.index_stage = "extracting"
    document.chunks_total = None
    document.chunks_done = None
    document.updated_at = now
    return document


def mark_indexed(
    session: Session,
    document_id: int,
    lease_owner: str,
    raw_text: str,
    parser_version: str,
) -> None:
    result = session.execute(
        update(Document)
        .where(Document.id == document_id, Document.lease_owner == lease_owner)
        .values(
            raw_text=raw_text,
            status="indexed",
            indexed_at=datetime.now(timezone.utc),
            last_error=None,
            parser_version=parser_version,
            index_stage="complete",
            queued_from_ui=False,
            lease_owner=None,
            lease_until=None,
            updated_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount != 1:
        raise RuntimeError(f"document {document_id} lease was lost before completion")


def mark_failed(session: Session, document_id: int, lease_owner: str, error: Exception) -> None:
    session.execute(
        update(Document)
        .where(Document.id == document_id, Document.lease_owner == lease_owner)
        .values(
            status="failed",
            last_error=str(error)[:4_000],
            queued_from_ui=False,
            lease_owner=None,
            lease_until=None,
            updated_at=datetime.now(timezone.utc),
        )
    )
