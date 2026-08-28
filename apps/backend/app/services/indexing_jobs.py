from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Event
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.db import session_scope
from app.models.document import Document
from app.models.index_run import IndexRun
from app.scripts.downloader import bulk_download_pdfs
from app.scripts.index_to_rag import index_pending_documents
from app.services.ingestion import MAX_RETRIES

logger = logging.getLogger(__name__)


class IndexingJobNotFoundError(LookupError):
    pass


class ActiveIndexingRunError(RuntimeError):
    pass


class IndexingJobService:
    """Persists indexing requests and controls for the external worker."""

    def start(self, collection: str, mode: str) -> dict:
        with session_scope() as session:
            active = session.scalar(
                select(IndexRun)
                .where(IndexRun.status.in_(["running", "paused"]))
                .order_by(IndexRun.started_at.desc())
                .limit(1)
            )
            if active is not None:
                raise ActiveIndexingRunError(
                    "An indexing run is already active; finish it before starting another"
                )

            run = IndexRun(
                run_id=uuid4(),
                collection=collection,
                status="running",
                metrics={
                    "mode": mode,
                    "indexed": 0,
                    "download_complete": mode != "all",
                },
            )
            session.add(run)
            run_id = run.run_id

        return self.get_status(run_id)

    def get_status(self, run_id: UUID) -> dict:
        with session_scope() as session:
            run = session.get(IndexRun, run_id)
            if run is None:
                raise IndexingJobNotFoundError(f"Indexing run '{run_id}' was not found")
            return self._serialize_run(session, run)

    def get_latest(self, collection: str) -> dict | None:
        with session_scope() as session:
            run = session.scalar(
                select(IndexRun)
                .where(IndexRun.collection == collection)
                .order_by(IndexRun.started_at.desc())
                .limit(1)
            )
            return None if run is None else self._serialize_run(session, run)

    def pause(self, run_id: UUID) -> dict:
        self._transition(run_id, "paused", allowed_from={"running"})
        return self.get_status(run_id)

    def resume(self, run_id: UUID) -> dict:
        self._transition(run_id, "running", allowed_from={"paused"})
        return self.get_status(run_id)

    def cancel(self, run_id: UUID) -> dict:
        self._transition(
            run_id,
            "cancelled",
            allowed_from={"running", "paused"},
            finished=True,
        )
        return self.get_status(run_id)

    def close(self) -> None:
        """The API service owns no background process."""

    def _transition(
        self,
        run_id: UUID,
        status: str,
        *,
        allowed_from: set[str],
        finished: bool = False,
    ) -> None:
        with session_scope() as session:
            run = session.get(IndexRun, run_id)
            if run is None:
                raise IndexingJobNotFoundError(f"Indexing run '{run_id}' was not found")
            if run.status not in allowed_from:
                return
            run.status = status
            if finished:
                run.finished_at = datetime.now(timezone.utc)

    @staticmethod
    def _serialize_run(session, run: IndexRun) -> dict:
        documents = session.scalars(
            select(Document)
            .where(Document.collection == run.collection)
            .order_by(Document.created_at, Document.id)
            .limit(100)
        ).all()
        total = session.scalar(
            select(func.count()).select_from(Document).where(Document.collection == run.collection)
        ) or 0
        completed = session.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.collection == run.collection, Document.status == "indexed")
        ) or 0
        now = run.finished_at or datetime.now(timezone.utc)
        elapsed_seconds = max(0, int((now - run.started_at).total_seconds()))

        return {
            "run_id": run.run_id,
            "collection": run.collection,
            "mode": (run.metrics or {}).get("mode", "pending"),
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "completed": completed,
            "total": total,
            "progress": 0 if not total else round(completed * 100 / total),
            "stage": _run_stage(run.status, documents),
            "elapsed_seconds": elapsed_seconds,
            "documents": [_serialize_document(document) for document in documents],
        }


class IndexingRunWorker:
    """Executes persisted indexing runs outside the FastAPI process."""

    def __init__(
        self,
        indexer: Callable[..., int] = index_pending_documents,
        downloader: Callable[[], list[str]] = bulk_download_pdfs,
    ) -> None:
        self._indexer = indexer
        self._downloader = downloader

    def run_once(self) -> bool:
        run = self._next_running_run()
        if run is None:
            return False

        run_id = run.run_id
        collection = run.collection
        metrics = dict(run.metrics or {})
        mode = metrics.get("mode", "pending")

        try:
            if mode == "all" and not metrics.get("download_complete", False):
                self._downloader()
                self._update_metrics(run_id, {"download_complete": True})

            if not self._is_running(run_id):
                return True

            try:
                self._indexer(
                    collection,
                    should_continue=lambda: self._is_running(run_id),
                )
            except Exception:
                logger.exception("An indexing attempt failed run_id=%s", run_id)

            self._finalize_attempt(run_id, collection)
        except Exception as error:
            error_message = str(error).strip() or type(error).__name__
            logger.exception("Indexing run failed run_id=%s", run_id)
            self._finish(
                run_id,
                "failed",
                metrics_update={"error": error_message[:4_000]},
            )
        return True

    def run_forever(self, stop_event: Event, *, poll_interval: float = 1.0) -> None:
        while not stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("Indexing worker polling failed")
            stop_event.wait(poll_interval)

    @staticmethod
    def _next_running_run() -> IndexRun | None:
        with session_scope() as session:
            return session.scalar(
                select(IndexRun)
                .where(IndexRun.status == "running")
                .order_by(IndexRun.started_at)
                .limit(1)
            )

    @staticmethod
    def _is_running(run_id: UUID) -> bool:
        with session_scope() as session:
            run = session.get(IndexRun, run_id)
            return run is not None and run.status == "running"

    @staticmethod
    def _update_metrics(run_id: UUID, metrics_update: dict) -> None:
        with session_scope() as session:
            run = session.get(IndexRun, run_id)
            if run is not None:
                run.metrics = {**(run.metrics or {}), **metrics_update}

    def _finalize_attempt(self, run_id: UUID, collection: str) -> None:
        with session_scope() as session:
            run = session.get(IndexRun, run_id)
            if run is None or run.status != "running":
                return

            documents = session.scalars(
                select(Document).where(Document.collection == collection)
            ).all()
            indexed = sum(document.status == "indexed" for document in documents)
            exhausted = [
                document
                for document in documents
                if document.status == "failed" and document.retries >= MAX_RETRIES
            ]
            run.metrics = {**(run.metrics or {}), "indexed": indexed}

            if exhausted:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.metrics = {
                    **run.metrics,
                    "error": exhausted[0].last_error
                    or f"{len(exhausted)} document(s) exhausted their retries",
                }
            elif indexed == len(documents):
                run.status = "completed"
                run.finished_at = datetime.now(timezone.utc)

    @staticmethod
    def _finish(
        run_id: UUID,
        status: str,
        *,
        metrics_update: dict | None = None,
    ) -> None:
        with session_scope() as session:
            run = session.get(IndexRun, run_id)
            if run is None or run.status != "running":
                return
            run.status = status
            run.finished_at = datetime.now(timezone.utc)
            if metrics_update:
                run.metrics = {**(run.metrics or {}), **metrics_update}


def _run_stage(status: str, documents: list[Document]) -> str:
    if status == "paused":
        return "En pausa"
    if status == "completed":
        return "Indexación completa"
    if status == "failed":
        return "Error de indexación"
    if status == "cancelled":
        return "Indexación cancelada"
    if any(document.status == "processing" for document in documents):
        return "Generando embeddings"
    if any(document.status == "pending" for document in documents):
        return "En cola"
    return "Esperando una acción"


def _serialize_document(document: Document) -> dict:
    stage_by_status = {
        "pending": "En cola",
        "processing": "Generando embeddings",
        "indexed": "Descargar → Extraer → Fragmentar → Vectorizar",
        "failed": "Error de indexación",
    }
    progress_by_status = {
        "pending": 0,
        "processing": 50,
        "indexed": 100,
        "failed": 0,
    }
    return {
        "id": document.id,
        "filename": document.filename,
        "source_url": document.source_url,
        "status": document.status,
        "stage": stage_by_status.get(document.status, "En cola"),
        "progress": progress_by_status.get(document.status, 0),
        "last_error": document.last_error,
    }
