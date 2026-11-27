"""Native RAGAS metrics (Faithfulness, Context Precision, Context Recall, Response Relevancy).

Implements the published RAGAS evaluation algorithms directly on top of the
configured LangChain chat judge (e.g., AWS Bedrock Nova Pro) and embedding
service (Bedrock Titan V2) without C-extension dependencies.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from collections.abc import Sequence
from typing import Any

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CITATION_TAG_RE = re.compile(r"\[S\d+\]")
REFUSAL_PHRASES = (
    "no encontré evidencia suficiente",
    "no tengo suficiente información",
    "no contienen la respuesta",
    "no lo sé",
)


class ClaimVerdict(BaseModel):
    claim: str = Field(description="Atomic factual statement extracted from the answer.")
    supported: bool = Field(
        description="True ONLY if the claim is directly entailed by the retrieved contexts."
    )
    reason: str = Field(description="Brief Spanish explanation citing why it is or is not supported.")


class FaithfulnessAssessment(BaseModel):
    claims: list[ClaimVerdict] = Field(
        default_factory=list,
        description="All atomic factual claims in the answer and whether the contexts support each.",
    )


class ContextRelevanceItem(BaseModel):
    index: int = Field(description="1-based index of the context chunk.")
    relevant: bool = Field(
        description="True if this context chunk helps answer the question accurately."
    )


class ContextPrecisionAssessment(BaseModel):
    verdicts: list[ContextRelevanceItem] = Field(default_factory=list)


class ReferenceStatementVerdict(BaseModel):
    statement: str = Field(description="Atomic factual statement from the reference answer.")
    attributed: bool = Field(
        description="True if the retrieved contexts contain enough evidence for this statement."
    )


class ContextRecallAssessment(BaseModel):
    statements: list[ReferenceStatementVerdict] = Field(default_factory=list)


class ReverseQuestionsAssessment(BaseModel):
    questions: list[str] = Field(
        default_factory=list,
        description="Three concise Spanish questions that the given answer directly answers.",
    )
    noncommittal: bool = Field(
        default=False,
        description="True if the answer refuses to answer or says it does not know.",
    )


class TurnEvaluation(BaseModel):
    faithfulness: float | None = None
    response_relevancy: float | None = None
    claims: list[ClaimVerdict] = Field(default_factory=list)
    judge_model: str = ""


class SampleEvaluation(TurnEvaluation):
    context_precision: float | None = None
    context_recall: float | None = None
    passed_refusal: bool | None = None


FAITHFULNESS_PROMPT = PromptTemplate.from_template(
    """You are a strict clinical RAG faithfulness judge for Peruvian DIGEMID drug leaflets.
Decompose the answer into atomic factual claims (dosages, indications, contraindications,
populations, warnings). Ignore citation tags like [S1].
For EACH claim, set supported=true if AT LEAST ONE retrieved context explicitly entails
or states that claim (it does NOT need to appear in all contexts).
Set supported=false if the claim contradicts the contexts, attributes a warning or dosage
to the wrong medicine, or adds facts not present in any retrieved context.
Write each reason concisely in Spanish.

Question: {question}

Retrieved contexts:
{contexts}

Answer:
{answer}"""
)

CONTEXT_PRECISION_PROMPT = PromptTemplate.from_template(
    """You are a RAG retrieval precision judge.
Evaluate EACH numbered context chunk (1..N) for whether it contains useful evidence to
answer the question accurately relative to the reference answer. Return one verdict per chunk.

Question: {question}

Reference answer: {reference_answer}

Numbered contexts:
{contexts}"""
)

CONTEXT_RECALL_PROMPT = PromptTemplate.from_template(
    """You are a RAG retrieval recall judge.
Break the reference answer into atomic factual statements. For each statement, set
attributed=true if AT LEAST ONE retrieved context contains enough evidence to support it,
even with minor paraphrasing or synonym differences. Set attributed=false only when the
information is missing from all retrieved contexts.

Reference answer: {reference_answer}

Retrieved contexts:
{contexts}"""
)

RESPONSE_RELEVANCY_PROMPT = PromptTemplate.from_template(
    """Given the following answer, generate 3 concise Spanish questions that this answer
directly addresses. If the answer says it does not know or lacks evidence, set
noncommittal=true.

Answer:
{answer}"""
)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def compute_context_precision(verdicts: Sequence[bool]) -> float:
    """RAGAS Mean Precision@k over ranked context relevance verdicts."""
    if not verdicts:
        return 0.0
    relevant_seen = 0
    precision_sum = 0.0
    for rank, is_relevant in enumerate(verdicts, start=1):
        if is_relevant:
            relevant_seen += 1
            precision_sum += relevant_seen / rank
    if relevant_seen == 0:
        return 0.0
    return round(precision_sum / relevant_seen, 4)


def compute_ratio(supported: int, total: int, *, empty_value: float = 1.0) -> float:
    if total <= 0:
        return empty_value
    return round(supported / total, 4)


def is_refusal_answer(answer: str) -> bool:
    lowered = answer.strip().lower()
    return any(phrase in lowered for phrase in REFUSAL_PHRASES)


def _format_contexts(contexts: Sequence[str]) -> str:
    if not contexts:
        return "(sin contextos recuperados)"
    return "\n\n".join(
        f"[{index}] {text.strip()}" for index, text in enumerate(contexts, start=1)
    )


def _strip_citations(answer: str) -> str:
    return " ".join(CITATION_TAG_RE.sub("", answer).split())


def _structured_method(model: Any) -> tuple[str, dict[str, Any]]:
    if type(model).__name__ == "ChatGroq":
        return "json_schema", {"strict": True}
    return "function_calling", {}


class RagasEvaluator:
    """Computes native RAGAS scores using a structured judge LLM and embeddings."""

    def __init__(
        self,
        judge_model: Any,
        embedding_service: Any,
        *,
        judge_model_name: str = "",
    ):
        self.judge_model = judge_model
        self.embedding_service = embedding_service
        self.judge_model_name = (
            judge_model_name
            or getattr(judge_model, "model_id", None)
            or getattr(judge_model, "model", None)
            or getattr(judge_model, "model_name", None)
            or type(judge_model).__name__
        )
        self._structured_cache: dict[type[BaseModel], Any] = {}

    def _structured(self, schema: type[BaseModel]) -> Any:
        if schema not in self._structured_cache:
            method, kwargs = _structured_method(self.judge_model)
            self._structured_cache[schema] = self.judge_model.with_structured_output(
                schema,
                method=method,
                **kwargs,
            )
        return self._structured_cache[schema]

    async def _invoke_structured(
        self,
        prompt: PromptTemplate,
        schema: type[BaseModel],
        variables: dict[str, str],
    ) -> Any:
        prompt_value = await prompt.ainvoke(variables)
        runner = self._structured(schema)
        for attempt in range(2):
            result = await runner.ainvoke(prompt_value)
            if result is not None:
                return result if isinstance(result, schema) else schema.model_validate(result)
            logger.warning(
                "Judge returned None for %s (attempt %d/2)",
                schema.__name__,
                attempt + 1,
            )
        return schema()

    async def score_faithfulness(
        self,
        question: str,
        answer: str,
        contexts: Sequence[str],
    ) -> tuple[float, list[ClaimVerdict]]:
        cleaned_answer = _strip_citations(answer)
        if not cleaned_answer or is_refusal_answer(cleaned_answer):
            return 1.0, []
        if not contexts:
            return 0.0, [
                ClaimVerdict(
                    claim=cleaned_answer[:200],
                    supported=False,
                    reason="No se recuperaron contextos de respaldo.",
                )
            ]

        assessment: FaithfulnessAssessment = await self._invoke_structured(
            FAITHFULNESS_PROMPT,
            FaithfulnessAssessment,
            {
                "question": question.strip(),
                "contexts": _format_contexts(contexts),
                "answer": cleaned_answer,
            },
        )
        claims = assessment.claims
        supported = sum(1 for item in claims if item.supported)
        return compute_ratio(supported, len(claims), empty_value=1.0), claims

    async def score_response_relevancy(
        self,
        question: str,
        answer: str,
    ) -> float:
        cleaned_answer = _strip_citations(answer)
        if not cleaned_answer or is_refusal_answer(cleaned_answer):
            return 0.0

        assessment: ReverseQuestionsAssessment = await self._invoke_structured(
            RESPONSE_RELEVANCY_PROMPT,
            ReverseQuestionsAssessment,
            {"answer": cleaned_answer},
        )
        generated = [q.strip() for q in assessment.questions if q.strip()][:3]
        if assessment.noncommittal or not generated:
            return 0.0

        vectors = await self.embedding_service.aembed_documents(
            [question.strip(), *generated]
        )
        question_vec, candidate_vecs = vectors[0], vectors[1:]
        scores = [cosine_similarity(question_vec, vec) for vec in candidate_vecs]
        return round(sum(scores) / len(scores), 4) if scores else 0.0

    async def score_context_precision(
        self,
        question: str,
        reference_answer: str,
        contexts: Sequence[str],
    ) -> float:
        if not contexts:
            return 0.0
        assessment: ContextPrecisionAssessment = await self._invoke_structured(
            CONTEXT_PRECISION_PROMPT,
            ContextPrecisionAssessment,
            {
                "question": question.strip(),
                "reference_answer": reference_answer.strip(),
                "contexts": _format_contexts(contexts),
            },
        )
        by_index = {item.index: item.relevant for item in assessment.verdicts}
        ordered = [by_index.get(idx, False) for idx in range(1, len(contexts) + 1)]
        return compute_context_precision(ordered)

    async def score_context_recall(
        self,
        reference_answer: str,
        contexts: Sequence[str],
    ) -> float:
        if not reference_answer.strip():
            return 1.0
        if not contexts:
            return 0.0
        assessment: ContextRecallAssessment = await self._invoke_structured(
            CONTEXT_RECALL_PROMPT,
            ContextRecallAssessment,
            {
                "reference_answer": reference_answer.strip(),
                "contexts": _format_contexts(contexts),
            },
        )
        statements = assessment.statements
        attributed = sum(1 for item in statements if item.attributed)
        return compute_ratio(attributed, len(statements), empty_value=0.0)

    async def evaluate_turn(
        self,
        *,
        question: str,
        answer: str,
        contexts: Sequence[str],
    ) -> TurnEvaluation:
        """Reference-free RAGAS check for live /chat opt-in evaluation."""
        faithfulness_result, relevancy = await asyncio.gather(
            self.score_faithfulness(question, answer, contexts),
            self.score_response_relevancy(question, answer),
        )
        faithfulness, claims = faithfulness_result
        return TurnEvaluation(
            faithfulness=faithfulness,
            response_relevancy=relevancy,
            claims=claims,
            judge_model=self.judge_model_name,
        )

    async def evaluate_sample(
        self,
        *,
        question: str,
        answer: str,
        contexts: Sequence[str],
        reference_answer: str = "",
        expected_refusal: bool = False,
    ) -> SampleEvaluation:
        """Full 4-metric RAGAS evaluation for golden dataset runs."""
        if expected_refusal:
            refused = is_refusal_answer(answer) or len(contexts) == 0
            return SampleEvaluation(
                faithfulness=1.0 if refused else 0.0,
                response_relevancy=None,
                context_precision=None,
                context_recall=None,
                passed_refusal=refused,
                claims=[],
                judge_model=self.judge_model_name,
            )

        (faithfulness, claims), relevancy, precision, recall = await asyncio.gather(
            self.score_faithfulness(question, answer, contexts),
            self.score_response_relevancy(question, answer),
            self.score_context_precision(question, reference_answer, contexts),
            self.score_context_recall(reference_answer, contexts),
        )
        return SampleEvaluation(
            faithfulness=faithfulness,
            response_relevancy=relevancy,
            context_precision=precision,
            context_recall=recall,
            passed_refusal=None,
            claims=claims,
            judge_model=self.judge_model_name,
        )
