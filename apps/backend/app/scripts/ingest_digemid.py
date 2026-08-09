"""Download DIGEMID PDFs and index all pending documents."""

import logging

from app.scripts.downloader import bulk_download_pdfs
from app.scripts.index_to_rag import index_pending_documents

logger = logging.getLogger(__name__)


def ingest_digemid() -> int:
    """Run the complete DIGEMID ingestion pipeline."""
    logger.info("Starting DIGEMID PDF download")
    bulk_download_pdfs()
    logger.info("Starting DIGEMID PDF indexing")
    return index_pending_documents()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    indexed = ingest_digemid()
    print(f"Indexed {indexed} document(s) with LangChain.")


if __name__ == "__main__":
    main()
