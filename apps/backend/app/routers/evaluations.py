from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from app.dependencies.providers import get_eval_store, get_ragas_evaluator
from app.routers.chat import limiter
from app.services.eval_store import EvalStore
from app.services.ragas_evaluator import RagasEvaluator, TurnEvaluation

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class TurnEvaluationRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=12000)
    contexts: list[str] = Field(default_factory=list, max_length=20)


@router.get("/runs", summary="List RAGAS evaluation runs")
async def list_evaluation_runs(
    limit: int = Query(default=20, ge=1, le=100),
    store: EvalStore = Depends(get_eval_store),
) -> dict[str, object]:
    runs = await asyncio.to_thread(store.list_runs, limit=limit)
    return {"runs": runs}


@router.get("/runs/{run_id}", summary="Get one RAGAS evaluation run with per-case results")
async def get_evaluation_run(
    run_id: int,
    store: EvalStore = Depends(get_eval_store),
) -> dict[str, object]:
    detail = await asyncio.to_thread(store.get_run_detail, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return detail


@router.post("/turn", summary="Evaluate a single chat turn with reference-free RAGAS")
@limiter.limit("10/minute")
async def evaluate_chat_turn(
    request: Request,
    response: Response,
    payload: TurnEvaluationRequest,
    evaluator: RagasEvaluator = Depends(get_ragas_evaluator),
) -> TurnEvaluation:
    return await evaluator.evaluate_turn(
        question=payload.question,
        answer=payload.answer,
        contexts=payload.contexts,
    )
