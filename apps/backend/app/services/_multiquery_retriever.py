import asyncio
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.settings import settings


class MultiqueryRetriever(BaseRetriever):
    vector_retriever: Any
    queries_generator: Any
    max_distance: float = settings.retrieval_max_distance
    max_results: int = settings.retrieval_max_results

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

    async def _retrieve_documents(
        self,
        query: str,
        history: str = "",
    ) -> list[Document]:
        generated_queries = await self.queries_generator.generate_queries(
            query,
            history=history,
        )
        queries = list(dict.fromkeys([query, *generated_queries]))
        results = await self.vector_retriever.retrieve_with_scores(queries)
        unique_results = [
            result
            for result in self.get_unique_union(results)
            if result[1] <= self.max_distance
        ][: self.max_results]
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
