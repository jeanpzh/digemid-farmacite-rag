import logging
import os

from app.db import _database_url, advisory_lock, session_scope
from app.services.ingestion import claim_document, mark_failed, mark_indexed
from app.services.langchain_indexer import (
    DEFAULT_EMBEDDING_MODEL,
    PARSER_VERSION,
    LangChainIndexer,
    make_embedding_service,
)
from langsmith import traceable

DEFAULT_COLLECTION = os.getenv("VECTOR_COLLECTION", "digemid")
logger = logging.getLogger(__name__)


@traceable(name="rag-index-pending-documents")
def index_pending_documents(collection: str = DEFAULT_COLLECTION) -> int:
    with advisory_lock():
        return _index_pending_documents(collection)


def _index_pending_documents(collection: str) -> int:
    from app.configs.scrapy_digemid import get_storage_client

    database_url = _database_url()

    storage = get_storage_client()
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")
    indexer = LangChainIndexer(
        database_url,
        make_embedding_service(os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)),
    )
    indexed = 0
    try:
        while True:
            with session_scope() as session:
                document = claim_document(session, collection)
                if document is None:
                    break
                document_id = document.id
                storage_key = document.storage_key
                filename = document.filename
                doc_hash = document.doc_hash
                lease_owner = document.lease_owner

            try:
                logger.info("Indexing pending PDF filename=%s", filename)
                contents = storage.storage.from_(bucket).download(storage_key)
                raw_text = indexer.index_pdf(contents, filename, collection, doc_hash)
                with session_scope() as session:
                    mark_indexed(session, document_id, lease_owner, raw_text, PARSER_VERSION)
            except Exception as error:
                logger.exception("Failed to index PDF filename=%s", filename)
                with session_scope() as session:
                    mark_failed(session, document_id, lease_owner, error)
                raise
            indexed += 1
    finally:
        indexer.close()
    logger.info("Finished indexing collection=%s documents=%d", collection, indexed)
    return indexed
def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    indexed = index_pending_documents()
    print(f"Indexed {indexed} document(s) with LangChain.")


if __name__ == "__main__":
    main()
