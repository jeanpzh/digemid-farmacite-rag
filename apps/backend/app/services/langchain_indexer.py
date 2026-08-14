import asyncio
import logging
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Iterator, TypeVar

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import Column as VectorColumn, PGEngine
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Column, Engine, Integer, MetaData, Table, Text, create_engine, delete
from sqlalchemy.dialects.postgresql import JSONB, insert

from app.settings import settings

logger = logging.getLogger(__name__)


async def close_pg_engine(engine: PGEngine) -> None:
    """Dispose a PGEngine and its async pool."""
    await engine.close()

VECTOR_SCHEMA = "rag"
VECTOR_TABLE = "langchain_embeddings"
EMBEDDING_DIMENSION = 768
PARSER_VERSION = "langchain-pypdf-recursive-1000-150"
METADATA_COLUMNS = ["collection", "doc_hash", "page", "start_index"]
CHUNK_SIZE = 1_000
CHUNK_OVERLAP = 150
EMBEDDING_BATCH_SIZE = 32
DB_WRITE_BATCH_SIZE = 200

metadata = MetaData()
embedding_table = Table(
    VECTOR_TABLE,
    metadata,
    Column("langchain_id", Text, primary_key=True),
    Column("content", Text, nullable=False),
    Column("embedding", VECTOR(EMBEDDING_DIMENSION), nullable=False),
    Column("collection", Text),
    Column("doc_hash", Text),
    Column("page", Integer),
    Column("start_index", Integer),
    Column("langchain_metadata", JSONB, nullable=False),
    schema=VECTOR_SCHEMA,
)

T = TypeVar("T")

SPLITTER = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", " ", ""],
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    add_start_index=True,
    strip_whitespace=True,
)


def chunk_id(collection: str, doc_hash: str, document: Document) -> str:
    page = document.metadata.get("page", 0)
    start_index = document.metadata.get("start_index", 0)
    identity = f"{collection}:{doc_hash}:{page}:{start_index}:{document.page_content}"
    return sha256(identity.encode("utf-8")).hexdigest()


def make_chunk_documents(
    pages: Iterable[Document],
    *,
    collection: str,
    doc_hash: str,
    filename: str | None = None,
    source_url: str | None = None,
) -> list[Document]:
    pages = list(pages)
    total_pages = len(pages)
    chunks = SPLITTER.split_documents(pages)
    result: list[Document] = []
    for chunk in chunks:
        metadata = {
            **chunk.metadata,
            "collection": collection,
            "doc_hash": doc_hash,
            "page": int(chunk.metadata.get("page", 0)),
            "start_index": int(chunk.metadata.get("start_index", 0)),
            "end_index": int(chunk.metadata.get("start_index", 0)) + len(chunk.page_content),
            "page_label": str(int(chunk.metadata.get("page", 0)) + 1),
            "total_pages": total_pages,
        }
        if filename is not None:
            metadata["filename"] = filename
        if source_url is not None:
            metadata["source_url"] = source_url
        normalized = Document(page_content=chunk.page_content, metadata=metadata)
        normalized.id = chunk_id(collection, doc_hash, normalized)
        normalized.metadata["chunk_id"] = normalized.id
        result.append(normalized)
    return result


def batch_items(items: list[T], size: int) -> Iterator[list[T]]:
    if size < 1:
        raise ValueError("batch size must be positive")
    for start in range(0, len(items), size):
        yield items[start : start + size]


def embed_documents_in_batches(
    embedding_service: Embeddings, texts: list[str]
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for batch in batch_items(texts, EMBEDDING_BATCH_SIZE):
        embeddings.extend(embedding_service.embed_documents(batch))
    return embeddings


def make_embedding_records(
    chunks: list[Document], embeddings: list[list[float]]
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        chunk_metadata = dict(chunk.metadata)
        records.append(
            {
                "langchain_id": chunk.id,
                "content": chunk.page_content,
                "embedding": embedding,
                "collection": chunk_metadata.pop("collection"),
                "doc_hash": chunk_metadata.pop("doc_hash"),
                "page": chunk_metadata.pop("page"),
                "start_index": chunk_metadata.pop("start_index"),
                "langchain_metadata": chunk_metadata,
            }
        )
    return records


class LangChainIndexer:
    def __init__(
        self,
        database_url: str,
        embedding_service: Embeddings,
        db_engine: Engine | None = None,
    ):
        self.db_engine = db_engine or create_engine(
            database_url,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )
        self.owns_db_engine = db_engine is None
        self.embedding_service = embedding_service

    def index_pdf(
        self,
        contents: bytes,
        filename: str,
        collection: str,
        doc_hash: str,
        source_url: str | None = None,
    ) -> str:
        suffix = Path(filename).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(suffix=suffix) as temporary_file:
            temporary_file.write(contents)
            temporary_file.flush()
            pages = PyPDFLoader(temporary_file.name).load()

        chunks = make_chunk_documents(
            pages,
            collection=collection,
            doc_hash=doc_hash,
            filename=filename,
            source_url=source_url,
        )
        if not chunks:
            raise ValueError("the document did not yield any indexable text")
        logger.info(
            "Loaded PDF filename=%s pages=%d chunks=%d",
            filename,
            len(pages),
            len(chunks),
        )

        embeddings = embed_documents_in_batches(
            self.embedding_service, [chunk.page_content for chunk in chunks]
        )
        records = make_embedding_records(chunks, embeddings)
        current_ids = [chunk.id for chunk in chunks]
        batch_count = (len(records) + DB_WRITE_BATCH_SIZE - 1) // DB_WRITE_BATCH_SIZE

        with self.db_engine.begin() as connection:
            for batch_number, batch in enumerate(
                batch_items(records, DB_WRITE_BATCH_SIZE), start=1
            ):
                statement = insert(embedding_table).values(batch)
                excluded = statement.excluded
                connection.execute(
                    statement.on_conflict_do_update(
                        index_elements=[embedding_table.c.langchain_id],
                        set_={
                            "content": excluded.content,
                            "embedding": excluded.embedding,
                            "collection": excluded.collection,
                            "doc_hash": excluded.doc_hash,
                            "page": excluded.page,
                            "start_index": excluded.start_index,
                            "langchain_metadata": excluded.langchain_metadata,
                        },
                    )
                )
                logger.info(
                    "Wrote PDF batch filename=%s batch=%d/%d chunks=%d",
                    filename,
                    batch_number,
                    batch_count,
                    len(batch),
                )

            connection.execute(
                delete(embedding_table).where(
                    embedding_table.c.collection == collection,
                    embedding_table.c.doc_hash == doc_hash,
                    embedding_table.c.langchain_id.not_in(current_ids),
                )
            )
        logger.info("Indexed PDF filename=%s chunks=%d", filename, len(chunks))
        return "\n\n".join(page.page_content for page in pages)

    def close(self) -> None:
        if self.owns_db_engine:
            self.db_engine.dispose()


def initialize_vector_table(database_url: str) -> None:
    engine = PGEngine.from_connection_string(
        url=database_url,
        pool_size=1,
        max_overflow=0,
    )
    try:
        engine.init_vectorstore_table(
            table_name=VECTOR_TABLE,
            schema_name=VECTOR_SCHEMA,
            vector_size=EMBEDDING_DIMENSION,
            id_column=VectorColumn("langchain_id", "TEXT", nullable=False),
            metadata_columns=[
                VectorColumn("collection", "TEXT"),
                VectorColumn("doc_hash", "TEXT"),
                VectorColumn("page", "INTEGER"),
                VectorColumn("start_index", "INTEGER"),
            ],
        )
    finally:
        asyncio.run(close_pg_engine(engine))
