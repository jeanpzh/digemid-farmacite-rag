"""Persistence layer for RAGAS evaluation runs and per-sample results."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Engine,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Text,
    desc,
    func,
    insert,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

eval_runs_table = Table(
    "eval_runs",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
    Column("git_sha", Text),
    Column("dataset_name", Text, nullable=False),
    Column("chat_provider", Text, nullable=False),
    Column("chat_model", Text, nullable=False),
    Column("router_model", Text, nullable=False),
    Column("embedding_model", Text, nullable=False),
    Column("judge_model", Text, nullable=False),
    Column("sample_count", Integer, nullable=False),
    Column("avg_faithfulness", Float),
    Column("avg_context_precision", Float),
    Column("avg_context_recall", Float),
    Column("avg_response_relevancy", Float),
    Column("avg_retrieval_ms", Float),
    Column("p95_retrieval_ms", Float),
    Column("avg_ttft_ms", Float),
    Column("refusal_accuracy", Float),
    Column("metadata", JSONB, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    schema="rag",
)

eval_results_table = Table(
    "eval_results",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("run_id", BigInteger, ForeignKey("rag.eval_runs.id", ondelete="CASCADE"), nullable=False),
    Column("case_id", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("question", Text, nullable=False),
    Column("history", Text, nullable=False, default=""),
    Column("reference_answer", Text, nullable=False, default=""),
    Column("generated_answer", Text, nullable=False),
    Column("retrieved_contexts", JSONB, nullable=False, default=list),
    Column("faithfulness", Float),
    Column("context_precision", Float),
    Column("context_recall", Float),
    Column("response_relevancy", Float),
    Column("retrieval_ms", Float),
    Column("ttft_ms", Float),
    Column("passed_refusal", Boolean),
    Column("claims", JSONB, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    schema="rag",
)


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(row)
    created_at = serialized.get("created_at")
    if isinstance(created_at, datetime):
        serialized["created_at"] = created_at.isoformat()
    return serialized


class EvalStore:
    def __init__(self, db_engine: Engine):
        self._engine = db_engine

    def save_run(
        self,
        run_payload: dict[str, Any],
        result_payloads: list[dict[str, Any]],
    ) -> int:
        with self._engine.begin() as connection:
            run_id = connection.execute(
                insert(eval_runs_table)
                .values(**run_payload)
                .returning(eval_runs_table.c.id)
            ).scalar_one()

            if result_payloads:
                connection.execute(
                    insert(eval_results_table).values(
                        [{"run_id": run_id, **item} for item in result_payloads]
                    )
                )
        return int(run_id)

    def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        statement = (
            select(eval_runs_table)
            .order_by(desc(eval_runs_table.c.created_at), desc(eval_runs_table.c.id))
            .limit(limit)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
            return [_serialize_row(dict(row)) for row in rows]

    def get_run_detail(self, run_id: int) -> dict[str, Any] | None:
        run_stmt = select(eval_runs_table).where(eval_runs_table.c.id == run_id)
        results_stmt = (
            select(eval_results_table)
            .where(eval_results_table.c.run_id == run_id)
            .order_by(eval_results_table.c.id.asc())
        )
        with self._engine.connect() as connection:
            run_row = connection.execute(run_stmt).mappings().one_or_none()
            if run_row is None:
                return None
            result_rows = connection.execute(results_stmt).mappings().all()
            return {
                "run": _serialize_row(dict(run_row)),
                "results": [_serialize_row(dict(row)) for row in result_rows],
            }
