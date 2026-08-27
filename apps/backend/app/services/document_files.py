import asyncio

from sqlalchemy import select

from app.models.document import Document as SourceDocument
from app.settings import settings
from app.services.document_storage import DocumentStorage, create_document_storage


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
        storage: DocumentStorage | None = None,
        *,
        collection: str = settings.vector_collection,
    ):
        self._metadata_engine = metadata_engine
        self._storage = storage or create_document_storage()
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

        return await asyncio.to_thread(self._create_signed_url, document["storage_key"])

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
        return self._storage.create_download_url(storage_key, SIGNED_URL_TTL_SECONDS)
