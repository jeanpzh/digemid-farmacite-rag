from app.services.query_generator import QueryGenerator
from app.services.query_router import QueryRouter
from app.services.response_generator import ResponseGenerator
from app.services.context_builder import ContextBuilder
from app.services._multiquery_retriever import MultiqueryRetriever
from app.services.chat import ChatService
from app.services.vector_retriever import VectorRetriever
from app.settings import settings


def create_chat_service(
    model,
    vector_store,
    metadata_engine=None,
    router_model=None,
) -> ChatService:
    effective_router_model = router_model or model

    retriever = MultiqueryRetriever(
        vector_retriever=VectorRetriever(
            vector_store,
            collection=settings.vector_collection,
            metadata_engine=metadata_engine,
        ),
        query_router=QueryRouter(model=effective_router_model),
        queries_generator=QueryGenerator(model=effective_router_model),
        max_distance=settings.retrieval_max_distance,
        min_results=settings.retrieval_min_results,
        max_results=settings.retrieval_max_results,
        expansion_max_queries=settings.retrieval_expansion_max_queries,
    )

    response_generator = ResponseGenerator(
        model=model
    )

    return ChatService(
        context_formatter=ContextBuilder(),
        document_retriever=retriever,
        answer_streamer=response_generator,
    )
