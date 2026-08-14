from collections.abc import Sequence
from hashlib import sha256

from langchain_core.documents import Document
from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

from app.schemas.chat_events import (
    Citation,
    CitationLocation,
    CitationSource,
)

MAX_CITATIONS = 30
MAX_EXCERPT_LENGTH = 1_000
_HTTP_URL = TypeAdapter(AnyHttpUrl)


def build_citations(documents: Sequence[Document]) -> list[Citation]:
    return [
        _build_citation(document, index)
        for index, document in enumerate(documents[:MAX_CITATIONS], start=1)
    ]


def _build_citation(document: Document, index: int) -> Citation:
    metadata = document.metadata
    document_id = _optional_text(metadata.get("document_id")) or "unknown"
    document_version = _optional_text(metadata.get("document_version")) or str(
        metadata.get("doc_hash") or "unknown"
    )
    chunk_id = str(document.id or metadata.get("chunk_id") or "unknown")
    label = f"S{index}"
    stable_key = ":".join(
        (
            document_id,
            document_version,
            chunk_id,
            str(metadata.get("page", "unknown")),
            str(metadata.get("start_index", "unknown")),
        )
    )
    start_index = _integer_metadata(metadata.get("start_index"), default=0)
    end_index = max(
        start_index,
        _integer_metadata(
            metadata.get("end_index"),
            default=start_index + len(document.page_content),
        ),
    )
    total_pages = _optional_integer(metadata.get("total_pages"))

    return Citation(
        id=f"cit_{sha256(stable_key.encode('utf-8')).hexdigest()[:16]}",
        label=label,
        source=CitationSource(
            document_id=document_id,
            document_version=document_version,
            chunk_id=chunk_id,
            filename=str(metadata.get("filename") or "unknown"),
            url=_optional_url(metadata.get("source_url")),
        ),
        location=CitationLocation(
            page=_page_number(metadata.get("page")),
            page_label=_optional_text(metadata.get("page_label")),
            total_pages=total_pages if total_pages and total_pages > 0 else None,
            start_index=start_index,
            end_index=end_index,
        ),
        excerpt=document.page_content[:MAX_EXCERPT_LENGTH],
    )


def _page_number(value: object) -> int:
    try:
        return max(0, int(value)) + 1
    except (TypeError, ValueError):
        return 1


def _integer_metadata(value: object, *, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _optional_integer(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_text(value: object) -> str | None:
    return str(value) if value is not None else None


def _optional_url(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(_HTTP_URL.validate_python(value))
    except (TypeError, ValueError, ValidationError):
        return None
