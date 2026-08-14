import asyncio
from collections.abc import Sequence

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore, VectorStoreRetriever
from sqlalchemy import select

from app.models.document import Document as SourceDocument
from app.settings import settings

class VectorRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        k: int = 5,
        collection: str = settings.vector_collection,
        metadata_engine=None,
    ):
        self.k = k
        self.vector_store = vector_store
        self.collection = collection
        self.metadata_engine = metadata_engine

    def as_retriever(self) -> VectorStoreRetriever:
        return self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": self.k,
                "filter": {"collection": self.collection},
            },
        )

    async def retrieve_with_scores(
        self, queries: Sequence[str]
    ) -> list[tuple[Document, float]]:
        results = await asyncio.gather(
            *(
                self.vector_store.asimilarity_search_with_score(
                    query,
                    k=self.k,
                    filter={"collection": self.collection},
                )
                for query in queries
            )
        )
        return [item for result in results for item in result]

    async def enrich_documents(self, documents):
        if not documents or self.metadata_engine is None:
            return documents

        doc_hashes = {
            str(document.metadata["doc_hash"])
            for document in documents
            if document.metadata.get("doc_hash")
        }
        if not doc_hashes:
            return documents

        source_metadata = await asyncio.to_thread(
            self._load_source_metadata,
            doc_hashes,
        )
        for document in documents:
            source = source_metadata.get(str(document.metadata.get("doc_hash")))
            if source is None:
                continue
            document.metadata["filename"] = source["filename"]
            document.metadata["source_url"] = source["source_url"]
            document.metadata["document_id"] = str(source["id"])
            document.metadata["document_version"] = source["doc_hash"]
        return documents

    def _load_source_metadata(self, doc_hashes: set[str]) -> dict[str, dict]:
        statement = select(
            SourceDocument.id,
            SourceDocument.doc_hash,
            SourceDocument.filename,
            SourceDocument.source_url,
        ).where(
            SourceDocument.collection == self.collection,
            SourceDocument.doc_hash.in_(doc_hashes),
        )
        with self.metadata_engine.connect() as connection:
            rows = connection.execute(statement).mappings()
            return {row["doc_hash"]: dict(row) for row in rows}
