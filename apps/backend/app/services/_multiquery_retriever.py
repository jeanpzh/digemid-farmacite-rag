
from langchain_core.documents import Document

from app.services.vector_retriever import VectorRetriever

class MultiqueryRetriever:
    def __init__(self, vector_retriever: VectorRetriever):
        self.vector_retriever = vector_retriever

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

    async def retrieve(self, queries: list[str]) -> list[tuple[Document, float]]:
        results = await self.vector_retriever.retrieve_with_scores(queries)
        unique_results = self.get_unique_union(results)[: self.vector_retriever.k]
        documents = await self.vector_retriever.enrich_documents(
            [document for document, _ in unique_results]
        )
        return [
            (document, distance)
            for document, (_, distance) in zip(documents, unique_results, strict=True)
        ]
