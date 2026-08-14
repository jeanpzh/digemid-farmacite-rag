"""Contract tests for the LangChain-based Supabase RAG indexer."""

from langchain_core.documents import Document as LangChainDocument

from app.services.langchain_indexer import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    LangChainIndexer,
    SPLITTER,
    batch_items,
    chunk_id,
    make_embedding_records,
    make_chunk_documents,
)


def test_langchain_splitter_preserves_page_metadata_and_is_deterministic():
    pages = [
        LangChainDocument(
            page_content="alpha beta gamma delta " * 30,
            metadata={"page": 2, "source": "source.pdf"},
        )
    ]

    first = make_chunk_documents(pages, collection="digemid", doc_hash="a" * 64)
    second = make_chunk_documents(pages, collection="digemid", doc_hash="a" * 64)

    assert first == second
    assert first
    assert all(chunk.metadata["collection"] == "digemid" for chunk in first)
    assert all(chunk.metadata["doc_hash"] == "a" * 64 for chunk in first)
    assert all(chunk.metadata["page"] == 2 for chunk in first)
    assert [chunk.id for chunk in first] == [
        chunk_id("digemid", "a" * 64, chunk) for chunk in first
    ]
    assert CHUNK_SIZE == 1_000
    assert CHUNK_OVERLAP == 150


def test_chunk_ids_change_when_collection_or_document_changes():
    page = LangChainDocument(page_content="same content", metadata={"page": 0})
    first = make_chunk_documents([page], collection="one", doc_hash="a" * 64)[0]
    second = make_chunk_documents([page], collection="two", doc_hash="a" * 64)[0]
    third = make_chunk_documents([page], collection="one", doc_hash="b" * 64)[0]

    assert len({first.id, second.id, third.id}) == 3


def test_batch_items_uses_the_actual_number_of_chunks():
    chunks = list(range(347))

    batches = list(batch_items(chunks, 200))

    assert [len(batch) for batch in batches] == [200, 147]
    assert [item for batch in batches for item in batch] == chunks


def test_make_embedding_records_preserves_chunk_data_and_metadata():
    chunk = LangChainDocument(
        id="chunk-id",
        page_content="contenido del chunk",
        metadata={
            "collection": "digemid",
            "doc_hash": "a" * 64,
            "page": 3,
            "start_index": 50,
            "source": "document.pdf",
        },
    )

    embedding = [0.25] * 768
    records = make_embedding_records([chunk], [embedding])

    assert records == [
        {
            "langchain_id": "chunk-id",
            "content": "contenido del chunk",
            "embedding": embedding,
            "collection": "digemid",
            "doc_hash": "a" * 64,
            "page": 3,
            "start_index": 50,
            "langchain_metadata": {"source": "document.pdf"},
        }
    ]


def test_index_pdf_writes_all_chunks_in_database_batches(monkeypatch):
    chunks = [
        LangChainDocument(
            id=f"chunk-{index}",
            page_content=f"chunk {index}",
            metadata={
                "collection": "digemid",
                "doc_hash": "a" * 64,
                "page": 0,
                "start_index": index,
            },
        )
        for index in range(347)
    ]
    inserted_batches = []

    class FakeStatement:
        class excluded:
            content = "content"
            embedding = "embedding"
            collection = "collection"
            doc_hash = "doc_hash"
            page = "page"
            start_index = "start_index"
            langchain_metadata = "langchain_metadata"

        def values(self, batch):
            inserted_batches.append(batch)
            return self

        def on_conflict_do_update(self, **kwargs):
            return self

    class FakeConnection:
        def __init__(self):
            self.executed = []

        def execute(self, statement):
            self.executed.append(statement)

    class FakeTransaction:
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, *args):
            return False

    connection = FakeConnection()
    indexer = LangChainIndexer.__new__(LangChainIndexer)
    indexer.db_engine = type(
        "FakeEngine", (), {"begin": lambda self: FakeTransaction(connection)}
    )()
    indexer.embedding_service = type(
        "FakeEmbeddings",
        (), {"embed_documents": lambda self, texts: [[0.0] * 768 for _ in texts]},
    )()

    monkeypatch.setattr(
        "app.services.langchain_indexer.PyPDFLoader",
        lambda _: type("FakeLoader", (), {"load": lambda self: []})(),
    )
    monkeypatch.setattr("app.services.langchain_indexer.make_chunk_documents", lambda *args, **kwargs: chunks)
    monkeypatch.setattr("app.services.langchain_indexer.insert", lambda _: FakeStatement())

    indexer.index_pdf(b"pdf", "document.pdf", "digemid", "a" * 64)

    assert [len(batch) for batch in inserted_batches] == [200, 147]
    assert len(connection.executed) == 3
