import asyncio
from collections.abc import Sequence

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore, VectorStoreRetriever
from langsmith import traceable
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
        if not queries:
            return []

        embeddings = getattr(self.vector_store, "embeddings", None)
        search_by_vector = getattr(
            self.vector_store,
            "asimilarity_search_with_score_by_vector",
            None,
        )
        embed_documents = getattr(embeddings, "aembed_documents", None)
        if embeddings is None or search_by_vector is None or embed_documents is None:
            return await self._retrieve_without_batching(queries)

        query_embeddings = await _embed_queries(
            embeddings=embeddings,
            queries=queries,
        )
        results = await asyncio.gather(
            *(
                _search_by_vector(
                    vector_store=self.vector_store,
                    embedding=embedding,
                    query=query,
                    k=self.k,
                    collection=self.collection,
                    query_index=index,
                )
                for index, (query, embedding) in enumerate(
                    zip(queries, query_embeddings, strict=True)
                )
            )
        )
        return [item for result in results for item in result]

    async def _retrieve_without_batching(
        self,
        queries: Sequence[str],
    ) -> list[tuple[Document, float]]:
        results = await asyncio.gather(
            *(
                _search_by_text(
                    vector_store=self.vector_store,
                    query=query,
                    k=self.k,
                    collection=self.collection,
                    query_index=index,
                )
                for index, query in enumerate(queries)
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

    @traceable(
        name="metadata_query",
        run_type="tool",
        process_inputs=lambda inputs: {
            "doc_hash_count": len(inputs.get("doc_hashes", ())),
        },
    )
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


@traceable(
    name="query_embedding_batch",
    run_type="embedding",
    process_inputs=lambda inputs: {
        "query_count": len(inputs.get("queries", ())),
    },
)
async def _embed_queries(*, embeddings, queries: Sequence[str]):
    return await embeddings.aembed_documents(list(queries))


@traceable(
    name="pgvector_search",
    run_type="retriever",
    process_inputs=lambda inputs: {
        "query": inputs.get("query"),
        "query_index": inputs.get("query_index"),
        "k": inputs.get("k"),
    },
)
async def _search_by_vector(
    *,
    vector_store,
    embedding,
    query: str,
    k: int,
    collection: str,
    query_index: int,
):
    return await vector_store.asimilarity_search_with_score_by_vector(
        embedding,
        k=k,
        filter={"collection": collection},
    )


@traceable(
    name="pgvector_search",
    run_type="retriever",
    process_inputs=lambda inputs: {
        "query": inputs.get("query"),
        "query_index": inputs.get("query_index"),
        "k": inputs.get("k"),
    },
)
async def _search_by_text(
    *,
    vector_store,
    query: str,
    k: int,
    collection: str,
    query_index: int,
):
    return await vector_store.asimilarity_search_with_score(
        query,
        k=k,
        filter={"collection": collection},
    )
