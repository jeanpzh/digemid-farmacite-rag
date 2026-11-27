import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies.providers import get_eval_store, get_ragas_evaluator
from app.routers.chat import limiter
from app.routers.evaluations import router as evaluations_router
from app.services.ragas_evaluator import (
    ClaimVerdict,
    ContextPrecisionAssessment,
    ContextRecallAssessment,
    ContextRelevanceItem,
    FaithfulnessAssessment,
    RagasEvaluator,
    ReferenceStatementVerdict,
    ReverseQuestionsAssessment,
    TurnEvaluation,
    compute_context_precision,
    cosine_similarity,
    is_refusal_answer,
)


class FakeStructuredRunner:
    def __init__(self, response):
        self._response = response

    async def ainvoke(self, prompt_value):
        return self._response


class FakeJudgeLLM:
    def __init__(self, responses: dict[type, object]):
        self._responses = responses
        self.model = "us.amazon.nova-pro-v1:0"

    def with_structured_output(self, schema, **kwargs):
        return FakeStructuredRunner(self._responses[schema])


class FakeEmbeddings:
    async def aembed_documents(self, texts):
        # First vector = [1, 0], generated candidates = [0.9, 0.43589] -> cosine ~ 0.9
        vectors = [[1.0, 0.0]]
        for _ in texts[1:]:
            vectors.append([0.9, 0.43588989435406733])
        return vectors


def test_compute_context_precision_rewards_top_ranked_relevant_chunks():
    assert compute_context_precision([True, True, False]) == 1.0
    assert compute_context_precision([False, True, False]) == 0.5
    assert compute_context_precision([False, False]) == 0.0


def test_cosine_similarity_and_refusal_detection():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert is_refusal_answer(
        "No encontré evidencia suficiente en las fuentes oficiales para responder esta consulta."
    )


def test_ragas_evaluator_computes_all_four_metrics_and_claims():
    judge = FakeJudgeLLM(
        {
            FaithfulnessAssessment: FaithfulnessAssessment(
                claims=[
                    ClaimVerdict(
                        claim="La dosis máxima es 16 g de gel al día.",
                        supported=True,
                        reason="Confirmado en la sección 3.2.",
                    ),
                    ClaimVerdict(
                        claim="Se puede aplicar en menores de 6 años.",
                        supported=False,
                        reason="El inserto indica a partir de 14 años.",
                    ),
                ]
            ),
            ReverseQuestionsAssessment: ReverseQuestionsAssessment(
                questions=[
                    "¿Cuál es la dosis máxima diaria de diclofenaco gel?",
                    "¿Cuántos gramos de diclofenaco gel se aplican al día?",
                ],
                noncommittal=False,
            ),
            ContextPrecisionAssessment: ContextPrecisionAssessment(
                verdicts=[
                    ContextRelevanceItem(index=1, relevant=True),
                    ContextRelevanceItem(index=2, relevant=False),
                    ContextRelevanceItem(index=3, relevant=True),
                ]
            ),
            ContextRecallAssessment: ContextRecallAssessment(
                statements=[
                    ReferenceStatementVerdict(statement="Dosis máxima 16 g/día.", attributed=True),
                    ReferenceStatementVerdict(statement="Equivale a 160 mg.", attributed=True),
                ]
            ),
        }
    )
    evaluator = RagasEvaluator(judge_model=judge, embedding_service=FakeEmbeddings())

    result = asyncio.run(
        evaluator.evaluate_sample(
            question="¿Cuál es la dosis máxima de diclofenaco gel?",
            answer="La dosis máxima es 16 g de gel al día [S1]. Se puede aplicar en menores de 6 años.",
            contexts=["Contexto 1", "Contexto 2", "Contexto 3"],
            reference_answer="La dosis máxima diaria es de 16 g de gel (160 mg).",
        )
    )

    assert result.faithfulness == 0.5
    assert result.response_relevancy == 0.9
    assert result.context_precision == round((1.0 + 2 / 3) / 2, 4)
    assert result.context_recall == 1.0
    assert result.passed_refusal is None
    assert len(result.claims) == 2
    assert result.judge_model == "us.amazon.nova-pro-v1:0"


def test_ragas_evaluator_scores_out_of_domain_refusal_deterministically():
    judge = FakeJudgeLLM({})
    evaluator = RagasEvaluator(judge_model=judge, embedding_service=FakeEmbeddings())

    result = asyncio.run(
        evaluator.evaluate_sample(
            question="¿Cómo preparar ceviche?",
            answer="No encontré evidencia suficiente en las fuentes oficiales para responder esta consulta.",
            contexts=[],
            expected_refusal=True,
        )
    )

    assert result.passed_refusal is True
    assert result.faithfulness == 1.0
    assert result.context_precision is None


def test_evaluations_http_endpoints():
    limiter.reset()

    class FakeStore:
        def list_runs(self, *, limit: int = 20):
            return [{"id": 1, "name": "bedrock-run", "sample_count": 10}]

        def get_run_detail(self, run_id: int):
            if run_id != 1:
                return None
            return {
                "run": {"id": 1, "name": "bedrock-run", "sample_count": 10},
                "results": [{"id": 10, "case_id": "case-1", "faithfulness": 0.95}],
            }

    class FakeEvaluator:
        async def evaluate_turn(self, *, question, answer, contexts):
            return TurnEvaluation(
                faithfulness=0.95,
                response_relevancy=0.88,
                claims=[
                    ClaimVerdict(
                        claim="Dosis máxima 16 g/día.",
                        supported=True,
                        reason="Respaldado por la ficha técnica.",
                    )
                ],
                judge_model="us.amazon.nova-pro-v1:0",
            )

    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(evaluations_router, prefix="/api/v1")
    app.dependency_overrides[get_eval_store] = lambda: FakeStore()
    app.dependency_overrides[get_ragas_evaluator] = lambda: FakeEvaluator()

    with TestClient(app) as client:
        runs_resp = client.get("/api/v1/evaluations/runs")
        detail_resp = client.get("/api/v1/evaluations/runs/1")
        missing_resp = client.get("/api/v1/evaluations/runs/999")
        turn_resp = client.post(
            "/api/v1/evaluations/turn",
            json={
                "question": "¿Dosis máxima?",
                "answer": "16 g/día.",
                "contexts": ["La dosis máxima es 16 g de gel al día."],
            },
        )

    assert runs_resp.status_code == 200
    assert runs_resp.json()["runs"][0]["id"] == 1
    assert detail_resp.status_code == 200
    assert detail_resp.json()["results"][0]["case_id"] == "case-1"
    assert missing_resp.status_code == 404
    assert turn_resp.status_code == 200
    assert turn_resp.json()["faithfulness"] == 0.95
    assert turn_resp.json()["claims"][0]["supported"] is True
