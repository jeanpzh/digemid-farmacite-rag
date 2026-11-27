import asyncio
import os
import logging
from contextlib import asynccontextmanager, suppress
from functools import partial

from app.dependencies.chat import create_chat_service
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.routers.chat import limiter, router as chat_router
from app.routers.configuration import router as configuration_router
from app.routers.document_library import router as document_library_router
from app.scripts.index_to_rag import index_uploaded_documents
from app.routers.documents import router as documents_router
from app.routers.evaluations import router as evaluations_router
from app.infraestructure.embeddings import create_embedding_service
from app.infraestructure.llm import create_judge_model, create_model, create_router_model
from app.infraestructure.vector_store import create_vector_store
from app.db import engine, vector_engine
from app.services.document_files import DocumentFileService
from app.services.eval_store import EvalStore
from app.services.ragas_evaluator import RagasEvaluator
from app.settings import settings

logger = logging.getLogger(__name__)


async def process_source_uploads() -> None:
    while True:
        try:
            await asyncio.to_thread(index_uploaded_documents, settings.vector_collection)
        except Exception:
            logger.exception("Source indexing worker failed")
        await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):

    pg_engine = vector_engine()

    embedding_service = create_embedding_service()

    model = create_model()
    router_model = create_router_model()
    judge_model = create_judge_model()
    metadata_engine = engine()

    vector_store = create_vector_store(
        engine=pg_engine,
        embedding_service=embedding_service,
    )
    chat_factory = partial(
        create_chat_service,
        vector_store=vector_store,
        model=model,
        router_model=router_model,
        metadata_engine=metadata_engine,
    )
    app.state.chat_service = chat_factory()
    app.state.test_chat_factory = chat_factory
    app.state.pipeline_test_lock = asyncio.Lock()
    app.state.document_file_service = DocumentFileService(
        metadata_engine=metadata_engine,
    )
    app.state.eval_store = EvalStore(db_engine=metadata_engine)
    app.state.ragas_evaluator = RagasEvaluator(
        judge_model=judge_model,
        embedding_service=embedding_service,
        judge_model_name=settings.eval_judge_model,
    )
    source_worker = asyncio.create_task(process_source_uploads()) if settings.source_library_enabled else None
    try:
        yield
    finally:
        if source_worker is not None:
            source_worker.cancel()
            with suppress(asyncio.CancelledError):
                await source_worker


app = FastAPI(
    title = "RAG DIGEMID",
    description = "RAG DIGEMID API for document retrieval and question answering",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["DELETE", "GET", "PATCH", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(configuration_router, prefix="/api/v1")
app.include_router(document_library_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(evaluations_router, prefix="/api/v1")

@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
