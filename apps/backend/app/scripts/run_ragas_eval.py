"""CLI runner that executes the DIGEMID golden dataset and persists RAGAS scores."""

from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_postgres import PGEngine, PGVectorStore

from app.db import _database_url, engine
from app.dependencies.chat import create_chat_service
from app.infraestructure.embeddings import create_embedding_service
from app.infraestructure.llm import create_judge_model, create_model, create_router_model
from app.services.eval_store import EvalStore
from app.services.golden_evaluation import (
    DEFAULT_DATASET_PATH,
    evaluate_case,
    load_cases,
    summarize_evaluation,
)
from app.services.ragas_evaluator import RagasEvaluator
from app.settings import settings

logger = logging.getLogger(__name__)


def _git_sha() -> str | None:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return output or None
    except Exception:
        return None


async def run_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    run_name: str | None = None,
    limit: int | None = None,
) -> int:
    cases: list[dict[str, Any]] = load_cases(dataset_path)
    if limit is not None:
        cases = cases[:limit]

    embedding_service = create_embedding_service()
    chat_model = create_model()
    router_model = create_router_model()
    judge_model = create_judge_model()
    metadata_engine = engine()

    pg_engine = PGEngine.from_connection_string(
        url=_database_url(),
        pool_size=settings.db_pool_max_size,
        max_overflow=0,
    )
    try:
        vector_store = await PGVectorStore.create(
            engine=pg_engine,
            embedding_service=embedding_service,
            schema_name=settings.schema_name,
            table_name=settings.table_name,
            metadata_columns=list(settings.metadata_columns),
        )
        chat_service = create_chat_service(
            model=chat_model,
            router_model=router_model,
            vector_store=vector_store,
            metadata_engine=metadata_engine,
        )
        evaluator = RagasEvaluator(
            judge_model=judge_model,
            embedding_service=embedding_service,
            judge_model_name=settings.eval_judge_model,
        )
        store = EvalStore(db_engine=metadata_engine)

        # Warm up pools and collection metadata cache so timings reflect steady state.
        async for _ in chat_service.stream([HumanMessage(content="dosis de paracetamol")]):
            pass

        result_payloads: list[dict[str, Any]] = []
        for idx, case in enumerate(cases, start=1):
            result = await evaluate_case(chat_service, evaluator, case)
            result_payloads.append(result)
            logger.info(
                "[%d/%d] %s (%s) | retrieval=%s ms | F=%s P=%s R=%s Rel=%s Refusal=%s",
                idx,
                len(cases),
                result["case_id"],
                result["category"],
                result["retrieval_ms"],
                result["faithfulness"],
                result["context_precision"],
                result["context_recall"],
                result["response_relevancy"],
                result["passed_refusal"],
            )

        run_payload = {
            "name": run_name or f"{settings.chat_provider}-{settings.model_name}",
            "git_sha": _git_sha(),
            "dataset_name": dataset_path.stem,
            "chat_provider": settings.chat_provider,
            "chat_model": settings.model_name,
            "router_model": settings.router_model_name,
            "embedding_model": settings.embedding_model,
            "judge_model": settings.eval_judge_model,
            "sample_count": len(result_payloads),
            **summarize_evaluation(result_payloads),
            "metadata": {
                "retrieval_max_distance": settings.retrieval_max_distance,
                "retrieval_min_results": settings.retrieval_min_results,
                "retrieval_max_results": settings.retrieval_max_results,
                "retrieval_expansion_max_queries": settings.retrieval_expansion_max_queries,
            },
        }
        run_id = store.save_run(run_payload, result_payloads)
        print(
            f"Saved RAGAS run #{run_id} ({run_payload['name']}): "
            f"samples={run_payload['sample_count']} "
            f"faithfulness={run_payload['avg_faithfulness']} "
            f"precision={run_payload['avg_context_precision']} "
            f"recall={run_payload['avg_context_recall']} "
            f"relevancy={run_payload['avg_response_relevancy']} "
            f"avg_retrieval_ms={run_payload['avg_retrieval_ms']} "
            f"p95_retrieval_ms={run_payload['p95_retrieval_ms']}"
        )
        return run_id
    finally:
        await pg_engine.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    parser = argparse.ArgumentParser(
        description="Run the DIGEMID golden RAGAS evaluation suite and save results to Supabase."
    )
    parser.add_argument("--name", default=None, help="Label for this evaluation run")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(
        run_evaluation(
            dataset_path=args.dataset,
            run_name=args.name,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
