"""Structured LLM router that resolves conversational references into one search route."""

import logging
from typing import Any

from langchain_core.prompts import PromptTemplate
from langsmith import traceable
from pydantic import BaseModel, Field

from app.configs.prompts import QUERY_ROUTER_PROMPT

logger = logging.getLogger(__name__)


class QueryRoute(BaseModel):
    search_query: str = Field(
        description=(
            "Single standalone Spanish search query with conversation references resolved."
        )
    )
    medicines: list[str] = Field(
        default_factory=list,
        description="Medicine names or active ingredients mentioned or referenced.",
    )
    intent: str = Field(
        default="general",
        description=(
            "Short clinical intent in snake_case (e.g. maximum_dose, dosage, "
            "contraindications, adverse_effects, interactions, comparison, general)."
        ),
    )


def _select_structured_method(model: Any) -> tuple[str, dict[str, Any]]:
    class_name = type(model).__name__
    if class_name == "ChatGroq":
        return "json_schema", {"strict": True}
    return "function_calling", {}


def _normalize_route(raw: QueryRoute | dict[str, Any], fallback_question: str) -> QueryRoute:
    route = raw if isinstance(raw, QueryRoute) else QueryRoute.model_validate(raw)
    raw_query = route.search_query.strip()
    if raw_query and "_" in raw_query and " " not in raw_query:
        raw_query = raw_query.replace("_", " ").strip()
    search_query = raw_query or fallback_question.strip()

    medicines: list[str] = []
    seen: set[str] = set()
    for item in route.medicines:
        cleaned = " ".join(str(item).strip().split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            medicines.append(cleaned)

    intent = "_".join(route.intent.strip().lower().split()) or "general"
    return QueryRoute(search_query=search_query, medicines=medicines, intent=intent)


class QueryRouter:
    """Calls a small LLM once per turn to produce a validated QueryRoute."""

    def __init__(
        self,
        model: Any,
        prompt: PromptTemplate = QUERY_ROUTER_PROMPT,
        *,
        structured_method: str | None = None,
    ):
        self.model = model
        self.prompt = prompt
        self._structured_method = structured_method
        self._structured_model: Any | None = None

    def _get_structured_model(self) -> Any:
        if self._structured_model is None:
            if self._structured_method is not None:
                method, kwargs = self._structured_method, {}
            else:
                method, kwargs = _select_structured_method(self.model)
            self._structured_model = self.model.with_structured_output(
                QueryRoute,
                method=method,
                **kwargs,
            )
        return self._structured_model

    @traceable(name="query_router", run_type="chain")
    async def route(self, question: str, history: str = "") -> QueryRoute:
        fallback = question.strip()
        if not fallback:
            return QueryRoute(search_query="", medicines=[], intent="general")

        try:
            prompt_value = await self.prompt.ainvoke(
                {
                    "question": fallback,
                    "history": history.strip() or "(sin historial)",
                }
            )
            result = await self._get_structured_model().ainvoke(prompt_value)
            return _normalize_route(result, fallback)
        except Exception:
            logger.warning(
                "QueryRouter failed; falling back to original question",
                exc_info=True,
            )
            return QueryRoute(search_query=fallback, medicines=[], intent="general")
