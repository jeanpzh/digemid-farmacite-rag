import os
from contextlib import asynccontextmanager

from app.dependencies.chat import create_chat_service
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat import router as chat_router
from app.infraestructure.embeddings import create_embedding_service
from app.infraestructure.llm import create_model
from app.infraestructure.vector_store import create_vector_store
from app.db import engine, vector_engine

@asynccontextmanager
async def lifespan(app: FastAPI):

    pg_engine = vector_engine()

    embedding_service = create_embedding_service()

    model = create_model()

    vector_store = create_vector_store(
        engine=pg_engine,
        embedding_service=embedding_service,
    )
    app.state.chat_service = create_chat_service(
        vector_store=vector_store,
        model=model,
        metadata_engine=engine(),
    )
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
    allow_methods=["DELETE", "GET", "PATCH", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(chat_router, prefix="/api/v1")

@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
