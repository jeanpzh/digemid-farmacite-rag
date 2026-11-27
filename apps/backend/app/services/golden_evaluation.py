"""Evaluate golden-dataset cases with the same pipeline used by chat."""

import json
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.schemas.chat_events import CitationsAvailable, RetrievalStatusChanged, TextDelta
from app.services.chat import ChatService, format_history
from app.services.ragas_evaluator import RagasEvaluator

DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[2] / "evals" / "digemid_golden.json"


def load_cases(dataset_path: Path = DEFAULT_DATASET_PATH) -> list[dict[str, Any]]:
    return json.loads(dataset_path.read_text(encoding="utf-8"))


def _mean(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 4)


def _percentile(values: list[float | None], pct: float) -> float | None:
    nums = sorted(v for v in values if v is not None)
    if not nums:
        return None
    idx = min(len(nums) - 1, max(0, int(round((pct / 100.0) * (len(nums) - 1)))))
    return round(nums[idx], 1)


def _build_messages(case: dict[str, Any]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for turn in case.get("history", []):
        role = turn.get("role")
        text = str(turn.get("text", "")).strip()
        if not text:
            continue
        if role == "assistant":
            messages.append(AIMessage(content=text))
        else:
            messages.append(HumanMessage(content=text))
    messages.append(HumanMessage(content=str(case["question"])))
    return messages


async def evaluate_case(
    chat_service: ChatService,
    evaluator: RagasEvaluator,
    case: dict[str, Any],
) -> dict[str, Any]:
    messages = _build_messages(case)
    history_str = format_history(messages[:-1])

    t_start = time.perf_counter()
    retrieval_ms: float | None = None
    t_after_retrieval: float | None = None
    ttft_ms: float | None = None
    answer_chunks: list[str] = []
    retrieved_contexts: list[dict[str, Any]] = []

    async for event in chat_service.stream(messages):
        if isinstance(event, RetrievalStatusChanged) and event.state == "complete":
            now = time.perf_counter()
            retrieval_ms = round((now - t_start) * 1000, 1)
            t_after_retrieval = now
        elif isinstance(event, CitationsAvailable):
            retrieved_contexts = [
                {
                    "filename": c.source.filename,
                    "page": c.location.page,
                    "snippet": c.excerpt,
                }
                for c in event.citations
            ]
        elif isinstance(event, TextDelta):
            if ttft_ms is None and t_after_retrieval is not None:
                ttft_ms = round((time.perf_counter() - t_after_retrieval) * 1000, 1)
            answer_chunks.append(event.text)

    generated_answer = "".join(answer_chunks).strip()
    context_texts = [item["snippet"] for item in retrieved_contexts if item.get("snippet")]

    scores = await evaluator.evaluate_sample(
        question=str(case["question"]),
        answer=generated_answer,
        contexts=context_texts,
        reference_answer=str(case.get("reference_answer", "")),
        expected_refusal=bool(case.get("expected_refusal", False)),
    )

    return {
        "case_id": str(case["case_id"]),
        "category": str(case["category"]),
        "question": str(case["question"]),
        "history": history_str,
        "reference_answer": str(case.get("reference_answer", "")),
        "generated_answer": generated_answer,
        "retrieved_contexts": retrieved_contexts,
        "faithfulness": scores.faithfulness,
        "context_precision": scores.context_precision,
        "context_recall": scores.context_recall,
        "response_relevancy": scores.response_relevancy,
        "retrieval_ms": retrieval_ms,
        "ttft_ms": ttft_ms,
        "passed_refusal": scores.passed_refusal,
        "claims": [claim.model_dump() for claim in scores.claims],
    }


def summarize_evaluation(results: list[dict[str, Any]]) -> dict[str, float | None]:
    refusal_checks = [
        1.0 if item["passed_refusal"] else 0.0
        for item in results
        if item["passed_refusal"] is not None
    ]
    return {
    "avg_faithfulness": _mean([r["faithfulness"] for r in results]),
    "avg_context_precision": _mean([r["context_precision"] for r in results]),
    "avg_context_recall": _mean([r["context_recall"] for r in results]),
    "avg_response_relevancy": _mean([r["response_relevancy"] for r in results]),
    "avg_retrieval_ms": _mean([r["retrieval_ms"] for r in results]),
    "p95_retrieval_ms": _percentile([r["retrieval_ms"] for r in results], 95),
    "avg_ttft_ms": _mean([r["ttft_ms"] for r in results]),
    "refusal_accuracy": _mean(refusal_checks),
    }
