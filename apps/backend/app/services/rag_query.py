import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langsmith import traceable

from app.configs.prompts import ANSWER_PROMPT
from app.schemas.rag_query import RAGCitation, RAGQueryRequest, RAGQueryResponse
from app.services.multiquery_retriever import retrieve_from_pgvector


def make_citations(documents: list[Document]) -> tuple[list[RAGCitation], str]:
    citations = []
    sources = []
    for document in documents:
        metadata = document.metadata
        if not document.id or not metadata.get("filename"):
            continue

        index = len(citations) + 1
        citation_id = f"S{index}"
        page = _metadata_int(metadata, "page", default=0)
        source_url = metadata.get("source_url")
        start_index = _metadata_int(metadata, "start_index", default=0)
        end_index = _metadata_int(
            metadata, "end_index", default=start_index + len(document.page_content)
        )
        citations.append(
            RAGCitation(
                id=citation_id,
                chunk_id=str(document.id),
                filename=str(metadata["filename"]),
                url=f"{source_url}#page={page + 1}" if source_url else None,
                page=page + 1,
                page_label=(
                    str(metadata["page_label"])
                    if metadata.get("page_label") is not None
                    else None
                ),
                total_pages=(
                    _metadata_int(metadata, "total_pages")
                    if _metadata_int(metadata, "total_pages") is not None
                    else None
                ),
                start_index=start_index,
                end_index=end_index,
                text=document.page_content,
            )
        )
        sources.append(f"[{citation_id}] {document.page_content}")
    return citations, "\n\n".join(sources)


def _metadata_int(
    metadata: dict[str, object], key: str, default: int | None = None
) -> int | None:
    value = metadata.get(key)
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


@traceable(name="rag-query", tags=["rag", "digemid"])
async def process_query(request: RAGQueryRequest) -> RAGQueryResponse:
    documents = await retrieve_from_pgvector(request.question)
    if not documents:
        return RAGQueryResponse(answer="No documents found")

    citations, sources = make_citations(documents)
    if not citations:
        return RAGQueryResponse(answer="No citable documents found")

    answer_chain = ANSWER_PROMPT | ChatGroq(
        model=os.getenv("ANSWER_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
    ) | StrOutputParser()
    answer = await answer_chain.ainvoke(
        {"question": request.question, "sources": sources}
    )
    return RAGQueryResponse(answer=answer, citations=citations)
