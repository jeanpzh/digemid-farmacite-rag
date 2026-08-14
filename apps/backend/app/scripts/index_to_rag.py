import logging
import os
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from threading import Event, Lock, local

from app.db import DB_POOL_MAX_SIZE, _database_url, advisory_lock, engine, session_scope
from app.infraestructure.embeddings import create_embedding_service
from app.models.document import Document
from app.services.ingestion import claim_document, mark_failed, mark_indexed
from app.services.langchain_indexer import (
    PARSER_VERSION,
    LangChainIndexer,
)
from langsmith import traceable

DEFAULT_COLLECTION = os.getenv("VECTOR_COLLECTION", "digemid")
MAX_INDEX_WORKERS = min(max(1, int(os.getenv("INDEX_WORKERS", "4"))), DB_POOL_MAX_SIZE)
logger = logging.getLogger(__name__)


@traceable(name="rag-index-pending-documents")
def index_pending_documents(collection: str = DEFAULT_COLLECTION) -> int:
    with advisory_lock():
        return _index_pending_documents(collection)


def _index_pending_documents(collection: str) -> int:
    from app.configs.scrapy_digemid import get_storage_client

    database_url = _database_url()

    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")
    shared_db_engine = engine()
    worker_state = local()
    worker_indexers: list[LangChainIndexer] = []
    worker_indexers_lock = Lock()
    indexed = 0

    def worker_resources() -> tuple[object, LangChainIndexer]:
        if not hasattr(worker_state, "indexer"):
            worker_state.storage = get_storage_client()
            worker_state.indexer = LangChainIndexer(
                database_url,
                create_embedding_service(),
                db_engine=shared_db_engine,
            )
            with worker_indexers_lock:
                worker_indexers.append(worker_state.indexer)
        return worker_state.storage, worker_state.indexer

    def index_document(document: Document) -> int:
        try:
            storage, indexer = worker_resources()
            logger.info("Indexing pending PDF filename=%s", document.filename)
            contents = storage.storage.from_(bucket).download(document.storage_key)
            raw_text = indexer.index_pdf(
                contents,
                document.filename,
                collection,
                document.doc_hash,
                document.source_url,
            )
            with session_scope() as session:
                mark_indexed(
                    session,
                    document.id,
                    document.lease_owner,
                    raw_text,
                    PARSER_VERSION,
                )
        except Exception as error:
            logger.exception("Failed to index PDF filename=%s", document.filename)
            with session_scope() as session:
                mark_failed(session, document.id, document.lease_owner, error)
            raise
        return 1

    try:
        with ThreadPoolExecutor(max_workers=MAX_INDEX_WORKERS) as executor:
            initializers_ready = Event()
            initialization_failed = Event()
            release_initializers = Event()
            initialized_workers = 0
            initialized_workers_lock = Lock()

            def initialize_worker() -> None:
                nonlocal initialized_workers
                try:
                    worker_resources()
                except Exception:
                    initialization_failed.set()
                    raise
                with initialized_workers_lock:
                    initialized_workers += 1
                    if initialized_workers == MAX_INDEX_WORKERS:
                        initializers_ready.set()
                release_initializers.wait()

            initializer_futures = [
                executor.submit(initialize_worker)
                for _ in range(MAX_INDEX_WORKERS)
            ]
            while not initializers_ready.wait(timeout=0.1):
                if initialization_failed.is_set():
                    release_initializers.set()
                    for future in initializer_futures:
                        future.result()
            release_initializers.set()
            for future in initializer_futures:
                future.result()

            futures: set[Future[int]] = set()
            exhausted = False

            while futures or not exhausted:
                while not exhausted and len(futures) < MAX_INDEX_WORKERS:
                    with session_scope() as session:
                        document = claim_document(session, collection)
                    if document is None:
                        exhausted = True
                        break
                    futures.add(executor.submit(index_document, document))

                if not futures:
                    continue

                completed, _ = wait(futures, return_when=FIRST_COMPLETED)
                futures.difference_update(completed)
                for future in completed:
                    indexed += future.result()
    finally:
        for indexer in worker_indexers:
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
