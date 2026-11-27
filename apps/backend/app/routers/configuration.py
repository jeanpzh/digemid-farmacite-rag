import asyncio
import json
import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.routers.chat import limiter
from app.services.golden_evaluation import (
    DEFAULT_DATASET_PATH,
    evaluate_case,
    load_cases,
    summarize_evaluation,
)
from app.settings import settings

router = APIRouter(prefix="/configuration", tags=["configuration"])
logger = logging.getLogger(__name__)


class PipelineModel(BaseModel):
    provider: str
    model: str


class PipelineRetrieval(BaseModel):
    max_distance: float
    min_results: int
    expansion_max_queries: int


class PipelineConfiguration(BaseModel):
    answer: PipelineModel
    router: PipelineModel
    embeddings: PipelineModel
    judge: PipelineModel
    retrieval: PipelineRetrieval
    trial_limits: PipelineRetrieval


TRIAL_LIMITS = PipelineRetrieval(
    max_distance=max(2, settings.retrieval_max_distance),
    min_results=max(settings.retrieval_max_results, settings.retrieval_min_results),
    expansion_max_queries=max(5, settings.retrieval_expansion_max_queries),
)


class PipelineTrial(PipelineRetrieval):
    model_config = ConfigDict(extra="forbid")

    max_distance: float = Field(ge=0, le=TRIAL_LIMITS.max_distance)
    min_results: int = Field(ge=1, le=TRIAL_LIMITS.min_results)
    expansion_max_queries: int = Field(ge=0, le=TRIAL_LIMITS.expansion_max_queries)


@router.get("/pipeline", summary="Get the active pipeline configuration")
def get_pipeline_configuration(response: Response) -> PipelineConfiguration:
    response.headers["Cache-Control"] = "no-store"
    return PipelineConfiguration(
        answer=PipelineModel(provider=settings.chat_provider, model=settings.model_name),
        router=PipelineModel(
            provider=settings.resolved_router_provider, model=settings.router_model_name
        ),
        embeddings=PipelineModel(
            provider=settings.embedding_provider, model=settings.embedding_model
        ),
        judge=PipelineModel(
            provider=settings.resolved_eval_provider, model=settings.eval_judge_model
        ),
        retrieval=PipelineRetrieval(
            max_distance=settings.retrieval_max_distance,
            min_results=settings.retrieval_min_results,
            expansion_max_queries=settings.retrieval_expansion_max_queries,
        ),
        trial_limits=TRIAL_LIMITS,
    )


def _trial_event(event_type: str, **data) -> str:
    return json.dumps({"type": event_type, **data}, allow_nan=False) + "\n"


@router.post("/pipeline/test", summary="Compare trial retrieval settings on the golden dataset")
@limiter.limit("2/minute")
async def test_pipeline(request: Request, trial: PipelineTrial):
    state = request.app.state

    async def stream():
        if state.pipeline_test_lock.locked():
            yield _trial_event("error", code="busy")
            return

        async with state.pipeline_test_lock:
            try:
                cases = await asyncio.to_thread(load_cases)
                if not cases:
                    raise ValueError("The golden dataset is empty")

                yield _trial_event("progress", completed=0, total=len(cases))
                baseline = state.test_chat_factory()
                candidate = state.test_chat_factory(**trial.model_dump())
                evaluator = state.ragas_evaluator
                baseline_results = []
                candidate_results = []

                async with asyncio.timeout(180):
                    for index, case in enumerate(cases):
                        if index % 2 == 0:
                            baseline_result = await evaluate_case(baseline, evaluator, case)
                            candidate_result = await evaluate_case(candidate, evaluator, case)
                        else:
                            candidate_result = await evaluate_case(candidate, evaluator, case)
                            baseline_result = await evaluate_case(baseline, evaluator, case)
                        baseline_results.append(baseline_result)
                        candidate_results.append(candidate_result)
                        yield _trial_event("progress", completed=index + 1, total=len(cases))

                yield _trial_event(
                    "result",
                    dataset=DEFAULT_DATASET_PATH.stem,
                    sample_count=len(cases),
                    baseline=summarize_evaluation(baseline_results),
                    candidate=summarize_evaluation(candidate_results),
                )
            except TimeoutError:
                yield _trial_event("error", code="timeout")
            except Exception:
                logger.exception("Pipeline test failed")
                yield _trial_event("error", code="failed")

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
