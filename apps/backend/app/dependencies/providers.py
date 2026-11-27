from fastapi import Request

from app.services.chat import ChatService
from app.services.eval_store import EvalStore
from app.services.ragas_evaluator import RagasEvaluator


def get_chat_service(
    request: Request,
) -> ChatService:
    return request.app.state.chat_service


def get_eval_store(
    request: Request,
) -> EvalStore:
    return request.app.state.eval_store


def get_ragas_evaluator(
    request: Request,
) -> RagasEvaluator:
    return request.app.state.ragas_evaluator
