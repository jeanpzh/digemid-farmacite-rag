"""Store uploaded PDFs and publish indexed versions into the chat corpus."""

import os
from datetime import date, datetime, timezone
from hashlib import sha256

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.db import advisory_lock, session_scope
from app.models.document import Document
from app.services.document_files import _default_storage_client
from app.services.ingestion import staged_collection
from app.services.langchain_indexer import embedding_table
from app.settings import settings

MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class LibraryConflict(Exception):
    pass


def document_view(document: Document) -> dict:
    error = None
    if document.status == "failed":
        error = (
            "El PDF no contiene texto extraíble."
            if "did not yield any indexable text" in (document.last_error or "")
            else "No se pudo procesar el PDF."
        )
    return {
        "id": str(document.id),
        "version": document.doc_hash,
        "filename": document.filename,
        "source_url": document.source_url,
        "origin": document.origin,
        "status": document.status,
        "publication": document.publication,
        "index_stage": document.index_stage,
        "chunks_total": document.chunks_total,
        "chunks_done": document.chunks_done,
        "error": error,
        "created_at": document.created_at,
        "indexed_at": document.indexed_at,
        "published_at": document.published_at,
        "updated_at": document.updated_at,
        "replaces_id": str(document.replaces_id) if document.replaces_id is not None else None,
        "effective_on": document.effective_on,
    }


def list_documents() -> list[dict]:
    with session_scope() as session:
        documents = session.scalars(
            select(Document)
            .where(Document.collection == settings.vector_collection)
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        return [document_view(document) for document in documents]


def store_upload(contents: bytes, filename: str) -> dict:
    collection = settings.vector_collection
    digest = sha256(contents).hexdigest()
    query = select(Document).where(
        Document.collection == collection, Document.doc_hash == digest
    )
    with session_scope() as session:
        existing = session.scalar(query)
        if existing is not None:
            return {"document": document_view(existing), "duplicate": True}

    key = f"{collection}/{digest}.pdf"
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")
    _default_storage_client().storage.from_(bucket).upload(
        key, contents, {"content-type": "application/pdf", "upsert": "true"}
    )

    with session_scope() as session:
        inserted = session.execute(
            insert(Document)
            .values(
                doc_hash=digest,
                filename=filename,
                storage_key=key,
                collection=collection,
                origin="upload",
                publication="review",
                queued_from_ui=True,
                status="pending",
            )
            .on_conflict_do_nothing(index_elements=[Document.collection, Document.doc_hash])
            .returning(Document.id)
        ).scalar_one_or_none()
        document = session.scalars(query).one()
        return {"document": document_view(document), "duplicate": inserted is None}


def retry_document(document_id: int) -> None:
    with session_scope() as session:
        result = session.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.collection == settings.vector_collection,
                Document.status == "failed",
                Document.publication != "archived",
            )
            .values(
                status="pending",
                queued_from_ui=True,
                retries=0,
                last_error=None,
                index_stage=None,
                chunks_total=None,
                chunks_done=None,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if result.rowcount != 1:
            raise LibraryConflict("El documento ya no se puede reintentar.")


def publish_document(
    document_id: int,
    *,
    replaces_id: int | None,
    source_url: str | None,
    effective_on: date | None,
) -> None:
    collection = settings.vector_collection
    staging = staged_collection(collection)
    with advisory_lock(), session_scope() as session:
        document = session.scalar(
            select(Document)
            .where(Document.id == document_id, Document.collection == collection)
            .with_for_update()
        )
        if document is None or document.status != "indexed" or document.publication != "review":
            raise LibraryConflict("El documento ya no está listo para publicación.")

        if replaces_id is not None:
            current = session.scalar(
                select(Document)
                .where(
                    Document.id == replaces_id,
                    Document.collection == collection,
                    Document.status == "indexed",
                    Document.publication == "published",
                )
                .with_for_update()
            )
            if current is None:
                raise LibraryConflict("La versión actual ya no está disponible.")
            session.execute(
                update(embedding_table)
                .where(
                    embedding_table.c.collection == collection,
                    embedding_table.c.doc_hash == current.doc_hash,
                )
                .values(collection=staging)
            )
            current.publication = "archived"
            current.updated_at = datetime.now(timezone.utc)

        result = session.execute(
            update(embedding_table)
            .where(
                embedding_table.c.collection == staging,
                embedding_table.c.doc_hash == document.doc_hash,
            )
            .values(collection=collection)
        )
        if not result.rowcount:
            raise LibraryConflict("No hay fragmentos indexados para publicar.")

        now = datetime.now(timezone.utc)
        document.publication = "published"
        document.replaces_id = replaces_id
        document.source_url = source_url
        document.effective_on = effective_on
        document.published_at = now
        document.updated_at = now
