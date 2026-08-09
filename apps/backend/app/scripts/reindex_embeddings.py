"""Reset a collection so every document is reindexed with the current model."""

import argparse
import os

from sqlalchemy import delete, func, update

from app.db import advisory_lock, session_scope
from app.models.document import Document
from app.models.embedding_config import EmbeddingConfig
from app.services.langchain_indexer import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    embedding_table,
)

DEFAULT_COLLECTION = os.getenv("VECTOR_COLLECTION", "digemid")
EMBEDDING_MODEL = (os.getenv("EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL).strip()


def reset_embedding_index(collection: str = DEFAULT_COLLECTION) -> int:
    """Delete old vectors and return all collection documents to the pending state."""
    with advisory_lock():
        with session_scope() as session:
            session.execute(
                delete(embedding_table).where(embedding_table.c.collection == collection)
            )
            result = session.execute(
                update(Document)
                .where(Document.collection == collection)
                .values(
                    status="pending",
                    retries=0,
                    last_error=None,
                    parser_version=None,
                    indexed_at=None,
                    lease_owner=None,
                    lease_until=None,
                    updated_at=func.now(),
                )
            )
            session.execute(
                update(EmbeddingConfig)
                .where(EmbeddingConfig.id.is_(True))
                .values(
                    model=EMBEDDING_MODEL,
                    embedding_dimension=EMBEDDING_DIMENSION,
                )
            )
    return result.rowcount or 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete vectors and reset documents for a full reindex."
    )
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm deletion of the collection's existing vectors",
    )
    args = parser.parse_args()
    if not args.yes:
        parser.error("--yes is required because this deletes existing vectors")

    reset_count = reset_embedding_index(args.collection)
    print(f"Reset {reset_count} document(s) in collection {args.collection!r}.")


if __name__ == "__main__":
    main()
