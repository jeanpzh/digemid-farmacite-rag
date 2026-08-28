from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.models.index_run import IndexRun
from app.services import indexing_jobs
from app.services.indexing_jobs import IndexingJobService


@pytest.fixture()
def indexing_session_scope(database_url, monkeypatch):
    normalized_url = database_url
    if normalized_url.startswith("postgresql://"):
        normalized_url = normalized_url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
    elif normalized_url.startswith("postgres://"):
        normalized_url = normalized_url.replace(
            "postgres://", "postgresql+psycopg://", 1
        )

    engine = create_engine(normalized_url, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()
    connection.execute(delete(IndexRun))
    factory = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    @contextmanager
    def test_session_scope():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(indexing_jobs, "session_scope", test_session_scope)
    try:
        yield test_session_scope
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()


def seed_run(session_scope, *, collection: str, status: str = "running"):
    run_id = uuid4()
    with session_scope() as session:
        session.add(
            IndexRun(
                run_id=run_id,
                collection=collection,
                status=status,
                started_at=datetime.now(timezone.utc),
                metrics={"mode": "pending", "indexed": 0},
            )
        )
    return run_id


def test_controls_survive_recreating_the_api_service(indexing_session_scope):
    run_id = seed_run(
        indexing_session_scope,
        collection=f"restart-controls-{uuid4()}",
    )
    service_after_restart = IndexingJobService()

    try:
        assert service_after_restart.pause(run_id)["status"] == "paused"
        assert service_after_restart.resume(run_id)["status"] == "running"
        assert service_after_restart.cancel(run_id)["status"] == "cancelled"
    finally:
        service_after_restart.close()


def test_worker_processes_a_run_created_before_it_started(indexing_session_scope):
    collection = f"restart-worker-{uuid4()}"
    run_id = seed_run(indexing_session_scope, collection=collection)
    indexed_collections = []

    worker_class = getattr(indexing_jobs, "IndexingRunWorker", None)
    assert worker_class is not None, "indexing must be executed by a restart-safe worker"

    def indexer(indexed_collection, should_continue):
        assert should_continue() is True
        indexed_collections.append(indexed_collection)
        return 0

    worker = worker_class(indexer=indexer, downloader=lambda: [])

    assert worker.run_once() is True
    assert indexed_collections == [collection]

    with indexing_session_scope() as session:
        run = session.get(IndexRun, run_id)
        assert run.status == "completed"
        assert run.finished_at is not None
