import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.query import router as query_router
from app.services.langchain_indexer import DEFAULT_EMBEDDING_MODEL, make_embedding_service


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    make_embedding_service(os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))
    yield

app = FastAPI(
    title = "RAG DIGEMID",
    description = "RAG DIGEMID API for document retrieval and question answering",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(query_router, prefix="/api/v1")

@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
