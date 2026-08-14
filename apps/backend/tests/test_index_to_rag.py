from contextlib import contextmanager
from threading import Event, Lock, Thread
from types import SimpleNamespace

from app.scripts import index_to_rag


@contextmanager
def fake_session_scope():
    yield object()


def test_indexes_documents_with_bounded_concurrency(monkeypatch):
    documents = [
        SimpleNamespace(
            id=index,
            storage_key=f"documents/{index}.pdf",
            filename=f"{index}.pdf",
            doc_hash=f"hash-{index}",
            lease_owner=f"lease-{index}",
            source_url=f"https://example.test/{index}.pdf",
        )
        for index in range(1, 4)
    ]
    claim_lock = Lock()
    active_lock = Lock()
    first_two_started = Event()
    release_workers = Event()
    active = 0
    peak_active = 0
    indexed = []
    shared_engine = object()
    indexer_engines = []
    indexer_lock = Lock()

    def claim_document(_session, collection):
        assert collection == "digemid"
        with indexer_lock:
            assert len(indexer_engines) == 2
        with claim_lock:
            return documents.pop(0) if documents else None

    class FakeIndexer:
        def __init__(self, *_args, **_kwargs):
            with indexer_lock:
                indexer_engines.append(_kwargs["db_engine"])

        def index_pdf(self, _contents, filename, _collection, _doc_hash, _source_url):
            nonlocal active, peak_active
            with active_lock:
                active += 1
                peak_active = max(peak_active, active)
                if active == 2:
                    first_two_started.set()

            release_workers.wait(timeout=1)

            with active_lock:
                active -= 1
            return f"text for {filename}"

        def close(self):
            pass

    storage = SimpleNamespace(
        storage=SimpleNamespace(
            from_=lambda _bucket: SimpleNamespace(
                download=lambda storage_key: storage_key.encode()
            )
        )
    )

    monkeypatch.setattr(index_to_rag, "MAX_INDEX_WORKERS", 2)
    monkeypatch.setattr(index_to_rag, "_database_url", lambda: "postgresql://test")
    monkeypatch.setattr(index_to_rag, "engine", lambda: shared_engine)
    monkeypatch.setattr(index_to_rag, "create_embedding_service", lambda: object())
    monkeypatch.setattr(index_to_rag, "LangChainIndexer", FakeIndexer)
    monkeypatch.setattr(index_to_rag, "session_scope", fake_session_scope)
    monkeypatch.setattr(index_to_rag, "claim_document", claim_document)
    monkeypatch.setattr(
        index_to_rag,
        "mark_indexed",
        lambda _session, document_id, lease_owner, raw_text, parser_version: indexed.append(
            (document_id, lease_owner, raw_text, parser_version)
        ),
    )
    monkeypatch.setattr(
        "app.configs.scrapy_digemid.get_storage_client", lambda: storage
    )

    result = []
    thread = Thread(
        target=lambda: result.append(index_to_rag._index_pending_documents("digemid"))
    )
    thread.start()
    assert first_two_started.wait(timeout=5)
    release_workers.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert result == [3]
    assert peak_active == 2
    assert indexer_engines and all(indexer_engine is shared_engine for indexer_engine in indexer_engines)
    assert sorted(indexed) == [
        (1, "lease-1", "text for 1.pdf", index_to_rag.PARSER_VERSION),
        (2, "lease-2", "text for 2.pdf", index_to_rag.PARSER_VERSION),
        (3, "lease-3", "text for 3.pdf", index_to_rag.PARSER_VERSION),
    ]


def test_marks_failed_documents_and_closes_worker_indexers(monkeypatch):
    document = SimpleNamespace(
        id=7,
        storage_key="documents/broken.pdf",
        filename="broken.pdf",
        doc_hash="broken-hash",
        lease_owner="lease-7",
        source_url="https://example.test/broken.pdf",
    )
    failed = []
    closed = []
    claimed = False

    class FakeIndexer:
        def __init__(self, *_args, **_kwargs):
            pass

        def index_pdf(self, *_args):
            raise ValueError("invalid PDF")

        def close(self):
            closed.append(True)

    storage = SimpleNamespace(
        storage=SimpleNamespace(
            from_=lambda _bucket: SimpleNamespace(download=lambda _key: b"broken")
        )
    )

    monkeypatch.setattr(index_to_rag, "MAX_INDEX_WORKERS", 1)
    monkeypatch.setattr(index_to_rag, "_database_url", lambda: "postgresql://test")
    monkeypatch.setattr(index_to_rag, "engine", lambda: object())
    monkeypatch.setattr(index_to_rag, "create_embedding_service", lambda: object())
    monkeypatch.setattr(index_to_rag, "LangChainIndexer", FakeIndexer)
    monkeypatch.setattr(index_to_rag, "session_scope", fake_session_scope)
    def claim_document(_session, _collection):
        nonlocal claimed
        if claimed:
            return None
        claimed = True
        return document

    monkeypatch.setattr(index_to_rag, "claim_document", claim_document)
    monkeypatch.setattr(
        index_to_rag,
        "mark_failed",
        lambda _session, document_id, lease_owner, error: failed.append(
            (document_id, lease_owner, str(error))
        ),
    )
    monkeypatch.setattr(
        "app.configs.scrapy_digemid.get_storage_client", lambda: storage
    )

    try:
        index_to_rag._index_pending_documents("digemid")
    except ValueError as error:
        assert str(error) == "invalid PDF"
    else:
        raise AssertionError("expected indexing to raise the worker error")

    assert failed == [(7, "lease-7", "invalid PDF")]
    assert closed == [True]


def test_waits_for_active_workers_before_reraising_a_failure(monkeypatch):
    documents = [
        SimpleNamespace(
            id=1,
            storage_key="documents/broken.pdf",
            filename="broken.pdf",
            doc_hash="broken-hash",
            lease_owner="lease-1",
            source_url="https://example.test/broken.pdf",
        ),
        SimpleNamespace(
            id=2,
            storage_key="documents/valid.pdf",
            filename="valid.pdf",
            doc_hash="valid-hash",
            lease_owner="lease-2",
            source_url="https://example.test/valid.pdf",
        ),
    ]
    claim_lock = Lock()
    broken_started = Event()
    valid_started = Event()
    release_valid = Event()
    failed = []
    indexed = []
    closed = []

    def claim_document(_session, _collection):
        with claim_lock:
            return documents.pop(0) if documents else None

    class FakeIndexer:
        def __init__(self, *_args, **_kwargs):
            pass

        def index_pdf(self, _contents, filename, *_args):
            if filename == "broken.pdf":
                broken_started.set()
                assert valid_started.wait(timeout=5)
                raise ValueError("invalid PDF")
            valid_started.set()
            assert release_valid.wait(timeout=5)
            return "valid text"

        def close(self):
            closed.append(True)

    storage = SimpleNamespace(
        storage=SimpleNamespace(
            from_=lambda _bucket: SimpleNamespace(download=lambda _key: b"pdf")
        )
    )

    monkeypatch.setattr(index_to_rag, "MAX_INDEX_WORKERS", 2)
    monkeypatch.setattr(index_to_rag, "_database_url", lambda: "postgresql://test")
    monkeypatch.setattr(index_to_rag, "engine", lambda: object())
    monkeypatch.setattr(index_to_rag, "create_embedding_service", lambda: object())
    monkeypatch.setattr(index_to_rag, "LangChainIndexer", FakeIndexer)
    monkeypatch.setattr(index_to_rag, "session_scope", fake_session_scope)
    monkeypatch.setattr(index_to_rag, "claim_document", claim_document)
    monkeypatch.setattr(
        index_to_rag,
        "mark_failed",
        lambda _session, document_id, lease_owner, error: failed.append(
            (document_id, lease_owner, str(error))
        ),
    )
    monkeypatch.setattr(
        index_to_rag,
        "mark_indexed",
        lambda _session, document_id, lease_owner, raw_text, parser_version: indexed.append(
            (document_id, lease_owner, raw_text, parser_version)
        ),
    )
    monkeypatch.setattr(
        "app.configs.scrapy_digemid.get_storage_client", lambda: storage
    )

    errors = []
    thread = Thread(
        target=lambda: _capture_error(
            lambda: index_to_rag._index_pending_documents("digemid"), errors
        )
    )
    thread.start()
    assert broken_started.wait(timeout=5)
    assert valid_started.wait(timeout=5)
    release_valid.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == ["invalid PDF"]
    assert failed == [(1, "lease-1", "invalid PDF")]
    assert indexed == [(2, "lease-2", "valid text", index_to_rag.PARSER_VERSION)]
    assert closed == [True, True]


def _capture_error(call, errors):
    try:
        call()
    except ValueError as error:
        errors.append(str(error))
