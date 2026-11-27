import asyncio
import unicodedata
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.services.query_router import QueryRoute
from app.settings import settings

INTENT_SEARCH_HINTS: dict[str, str] = {
    "maximum_dose": "dosis máxima diaria posología",
    "dosage": "posología dosis administración",
    "pediatric_dose": "dosis niños pediátrico posología",
    "contraindications": "contraindicaciones advertencias",
    "adverse_effects": "efectos adversos reacciones secundarias",
    "interactions": "interacciones otros medicamentos",
    "indications": "indicaciones terapéuticas uso",
    "pregnancy": "embarazo lactancia",
    "overdose": "sobredosis intoxicación",
}


def _normalize_for_match(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _document_search_text(document: Document) -> str:
    filename = str(document.metadata.get("filename") or "")
    return _normalize_for_match(f"{filename} {document.page_content}")


def find_missing_medicines(
    medicines: list[str],
    results: list[tuple[Document, float]],
) -> list[str]:
    if not medicines:
        return []
    haystacks = [_document_search_text(doc) for doc, _ in results]
    missing: list[str] = []
    for medicine in medicines:
        needle = _normalize_for_match(medicine).strip()
        if not needle:
            continue
        if not any(needle in haystack for haystack in haystacks):
            missing.append(medicine)
    return missing


def build_targeted_queries(
    route: QueryRoute,
    missing_medicines: list[str],
    *,
    already_searched: set[str],
    max_queries: int,
) -> list[str]:
    candidates: list[str] = []
    intent_hint = INTENT_SEARCH_HINTS.get(route.intent, "")
    for medicine in missing_medicines:
        query = f"{medicine} {intent_hint}".strip() if intent_hint else f"{medicine} {route.search_query}".strip()
        if query and query not in already_searched and query not in candidates:
            candidates.append(query)
        if len(candidates) >= max_queries:
            break
    return candidates[:max_queries]


class MultiqueryRetriever(BaseRetriever):
    vector_retriever: Any
    queries_generator: Any = None
    query_router: Any = None
    max_distance: float = settings.retrieval_max_distance
    min_results: int = settings.retrieval_min_results
    max_results: int = settings.retrieval_max_results
    expansion_max_queries: int = settings.retrieval_expansion_max_queries

    def get_unique_union(
        self, results: list[tuple[Document, float]]
    ) -> list[tuple[Document, float]]:
        unique_results: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[Document, float]] = {}
        for document, distance in results:
            key = (
                document.page_content,
                tuple(sorted((str(name), str(value)) for name, value in document.metadata.items())),
            )
            previous = unique_results.get(key)
            if previous is None or distance < previous[1]:
                unique_results[key] = (document, distance)
        return sorted(unique_results.values(), key=lambda result: result[1])

    def _filter_results(
        self, results: list[tuple[Document, float]]
    ) -> list[tuple[Document, float]]:
        return [
            result
            for result in self.get_unique_union(results)
            if result[1] <= self.max_distance
        ]

    async def _retrieve_with_router(
        self,
        query: str,
        history: str = "",
    ) -> list[Document]:
        route: QueryRoute = await self.query_router.route(query, history=history)
        primary_query = route.search_query or query

        # Pass 1: single focused search from the validated router output.
        all_results = await self.vector_retriever.retrieve_with_scores([primary_query])
        filtered = self._filter_results(all_results)

        # Deterministic coverage check: expand at most once if coverage is incomplete.
        missing_medicines = find_missing_medicines(route.medicines, filtered)
        needs_expansion = bool(missing_medicines) or len(filtered) < self.min_results

        if needs_expansion and self.expansion_max_queries > 0:
            searched = {primary_query}
            expansion_queries = build_targeted_queries(
                route,
                missing_medicines,
                already_searched=searched,
                max_queries=self.expansion_max_queries,
            )
            remaining_slots = self.expansion_max_queries - len(expansion_queries)
            if remaining_slots > 0 and len(filtered) < self.min_results:
                if self.queries_generator is not None:
                    generated = await self.queries_generator.generate_queries(
                        primary_query,
                        history=history,
                    )
                    for candidate in generated:
                        if candidate and candidate not in searched and candidate not in expansion_queries:
                            expansion_queries.append(candidate)
                        if len(expansion_queries) >= self.expansion_max_queries:
                            break
                elif query.strip() and query.strip() not in searched and query.strip() not in expansion_queries:
                    expansion_queries.append(query.strip())

            if expansion_queries:
                expanded_results = await self.vector_retriever.retrieve_with_scores(
                    expansion_queries[: self.expansion_max_queries]
                )
                all_results = [*all_results, *expanded_results]
                filtered = self._filter_results(all_results)

        selected = filtered[: self.max_results]
        return await self.vector_retriever.enrich_documents(
            [document for document, _ in selected]
        )

    async def _retrieve_documents(
        self,
        query: str,
        history: str = "",
    ) -> list[Document]:
        if self.query_router is not None:
            return await self._retrieve_with_router(query, history=history)

        generated_queries = await self.queries_generator.generate_queries(
            query,
            history=history,
        )
        queries = list(dict.fromkeys([query, *generated_queries]))
        results = await self.vector_retriever.retrieve_with_scores(queries)
        unique_results = self._filter_results(results)[: self.max_results]
        documents = await self.vector_retriever.enrich_documents(
            [document for document, _ in unique_results]
        )
        return documents

    def _get_relevant_documents(
        self,
        query: str,
        *,
        history: str = "",
        run_manager: Any,
    ) -> list[Document]:
        return asyncio.run(self._retrieve_documents(query, history=history))

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        history: str = "",
        run_manager: Any,
    ) -> list[Document]:
        return await self._retrieve_documents(query, history=history)
