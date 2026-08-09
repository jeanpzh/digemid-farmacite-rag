
from fastapi import APIRouter

from app.schemas.rag_query import RAGQueryRequest, RAGQueryResponse
from app.services.rag_query import process_query

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", summary="Query the RAG model with a question and retrieve relevant documents")
async def process_rag_query(request: RAGQueryRequest) -> RAGQueryResponse:
    return await process_query(request)
