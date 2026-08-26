from app.services.query_generator import QueryGenerator
from app.services.response_generator import ResponseGenerator
from app.services.context_builder import ContextBuilder
from app.services._multiquery_retriever import MultiqueryRetriever
from app.services.chat import ChatService
from app.services.vector_retriever import VectorRetriever
from app.settings import settings

def  create_chat_service(
    model,
    vector_store,
    metadata_engine=None,
) -> ChatService:

    retriever = MultiqueryRetriever(
        vector_retriever=VectorRetriever(
            vector_store,
            collection=settings.vector_collection,
            metadata_engine=metadata_engine,
        ),
        queries_generator=QueryGenerator(model=model),
        max_distance=settings.retrieval_max_distance,
        max_results=settings.retrieval_max_results,
    )

    response_generator = ResponseGenerator(
        model=model
    )

    return ChatService(
        context_formatter=ContextBuilder(),
        document_retriever=retriever,
        answer_streamer=response_generator,
    )
