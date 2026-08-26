import asyncio

from langchain_core.documents import Document

import app.services.vector_retriever as vector_retriever_module
from app.services.vector_retriever import VectorRetriever
from app.services._multiquery_retriever import MultiqueryRetriever
from app.dependencies.chat import create_chat_service


class FakeVectorStore:
    def as_retriever(self, **kwargs):
        self.kwargs = kwargs
        return object()


class ScoredVectorStore:
    async def asimilarity_search_with_score(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return [(Document(page_content=query), 0.2)]

    def __init__(self):
        self.calls = []


class EmbeddingService:
    def __init__(self):
        self.calls = []

    async def aembed_documents(self, queries):
        self.calls.append(list(queries))
        return [[float(len(query))] for query in queries]


class VectorSearchStore:
    def __init__(self):
        self.embeddings = EmbeddingService()
        self.calls = []

    async def asimilarity_search_with_score_by_vector(self, embedding, **kwargs):
        self.calls.append((embedding, kwargs))
        return [(Document(page_content="resultado"), 0.2)]


def test_vector_retriever_limits_search_to_configured_collection():
    vector_store = FakeVectorStore()

    VectorRetriever(vector_store, k=7, collection="digemid").as_retriever()

    assert vector_store.kwargs == {
        "search_type": "similarity",
        "search_kwargs": {
            "k": 7,
            "filter": {"collection": "digemid"},
        },
    }


def test_chat_service_composes_collection_filtered_retriever():
    service = create_chat_service(model=object(), vector_store=FakeVectorStore())

    retriever = service._document_retriever.vector_retriever

    assert isinstance(retriever, VectorRetriever)
    assert retriever.collection == "digemid"


def test_vector_retriever_returns_scored_collection_filtered_results():
    vector_store = ScoredVectorStore()
    retriever = VectorRetriever(vector_store, k=3, collection="digemid")

    results = asyncio.run(retriever.retrieve_with_scores(["consulta uno", "consulta dos"]))

    assert [document.page_content for document, _ in results] == [
        "consulta uno",
        "consulta dos",
    ]
    assert vector_store.calls == [
        ("consulta uno", {"k": 3, "filter": {"collection": "digemid"}}),
        ("consulta dos", {"k": 3, "filter": {"collection": "digemid"}}),
    ]


def test_vector_retriever_batches_query_embeddings_before_pgvector_search(monkeypatch):
    monkeypatch.setattr(
        vector_retriever_module,
        "_embed_queries",
        vector_retriever_module._embed_queries.__wrapped__,
    )
    monkeypatch.setattr(
        vector_retriever_module,
        "_search_by_vector",
        vector_retriever_module._search_by_vector.__wrapped__,
    )
    vector_store = VectorSearchStore()
    retriever = VectorRetriever(vector_store, k=3, collection="digemid")

    results = asyncio.run(retriever.retrieve_with_scores(["uno", "dos"]))

    assert [document.page_content for document, _ in results] == [
        "resultado",
        "resultado",
    ]
    assert vector_store.embeddings.calls == [["uno", "dos"]]
    assert vector_store.calls == [
        ([3.0], {"k": 3, "filter": {"collection": "digemid"}}),
        ([3.0], {"k": 3, "filter": {"collection": "digemid"}}),
    ]


def test_multiquery_retriever_keeps_lowest_distance_for_duplicates():
    retriever = MultiqueryRetriever(vector_retriever=object())
    document = Document(page_content="contenido", metadata={"page": 1})

    results = retriever.get_unique_union([(document, 0.6), (document, 0.2)])

    assert results == [(document, 0.2)]
