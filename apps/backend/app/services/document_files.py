import asyncio
import os
from collections.abc import Callable

from sqlalchemy import select

from app.models.document import Document as SourceDocument
from app.settings import settings


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: int, document_version: str):
        super().__init__(
            f"document {document_id} version {document_version} was not found"
        )


SIGNED_URL_TTL_SECONDS = 300


class DocumentFileService:
    def __init__(
        self,
        metadata_engine,
        storage_client_factory: Callable[[], object] | None = None,
        *,
        bucket: str | None = None,
        collection: str = settings.vector_collection,
    ):
        self._metadata_engine = metadata_engine
        self._storage_client_factory = storage_client_factory or _default_storage_client
        self._bucket = bucket or os.getenv("SUPABASE_STORAGE_BUCKET", "documents")
        self._collection = collection

    async def get_pdf_url(
        self,
        document_id: int,
        document_version: str,
    ) -> str:
        document = await asyncio.to_thread(
            self._find_document,
            document_id,
            document_version,
        )
        if document is None:
            raise DocumentNotFoundError(document_id, document_version)

        return await asyncio.to_thread(
            self._create_signed_url,
            document["storage_key"],
        )

    def _find_document(self, document_id: int, document_version: str):
        statement = select(
            SourceDocument.storage_key,
        ).where(
            SourceDocument.id == document_id,
            SourceDocument.doc_hash == document_version,
            SourceDocument.collection == self._collection,
        )
        with self._metadata_engine.connect() as connection:
            return connection.execute(statement).mappings().one_or_none()

    def _create_signed_url(self, storage_key: str) -> str:
        storage_client = self._storage_client_factory()
        response = storage_client.storage.from_(self._bucket).create_signed_url(
            storage_key,
            SIGNED_URL_TTL_SECONDS,
        )
        signed_url = response.get("signedURL") or response.get("signedUrl")
        if not signed_url:
            raise RuntimeError("Supabase did not return a signed PDF URL")
        return signed_url


def _default_storage_client():
    from app.configs.scrapy_digemid import get_storage_client

    return get_storage_client()
