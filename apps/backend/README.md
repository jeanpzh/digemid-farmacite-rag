# Backend

FastAPI service for cited RAG over DIGEMID PDFs. See the [root README](../../README.md) for full-stack setup.

## Run

From `apps/backend`:

```bash
uv sync --frozen
uv run uvicorn app.main:app --reload
```

Listens on `http://localhost:8000`. Verify with `curl -fsS http://localhost:8000/api/v1/health`.

## API

- `GET /api/v1/health` — liveness check.
- `POST /api/v1/chat` — accepts the current user message + up to 6 prior text turns; streams AI SDK data events (retrieval status, citations, answer deltas).

## Code Map

| Path | Responsibility |
| --- | --- |
| `app/routers/chat.py` | Chat endpoint & stream wiring |
| `app/adapters/` | Request normalization & AI SDK stream encoding |
| `app/infraestructure/embeddings.py` | Embedding factory (`bedrock` or `ollama`) |
| `app/services/chat.py` | Query expansion, retrieval, citations & answer orchestration |
| `app/services/vector_retriever.py` | `pgvector` search & metadata enrichment |
| `app/services/langchain_indexer.py` | PDF parsing, chunking, embeddings & vector writes |
| `app/scripts/` | Ingestion, indexing & reindex CLIs |
| `app/settings.py` | Pydantic runtime config & fail-fast validation |

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `SUPABASE_DB_URL` | *(required)* | PostgreSQL connection string |
| `CHAT_PROVIDER` | `groq` | `groq` or `ollama` |
| `GROQ_API_KEY` | — | Required when `CHAT_PROVIDER=groq` |
| `MODEL_NAME` | `qwen/qwen3.6-27b` | Chat model ID |
| `EMBEDDING_PROVIDER` | `bedrock` | `bedrock` or `ollama` |
| `EMBEDDING_MODEL` | `amazon.titan-embed-text-v2:0` | Embedding model ID |
| `EMBEDDING_DIMENSION` | `1024` | Must match `rag.langchain_embeddings` (`vector(1024)`) |
| `AWS_REGION` | `us-east-2` | Required when `EMBEDDING_PROVIDER=bedrock` |
| `AWS_PROFILE` | — | Local AWS profile; omit in prod to use IAM role |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Used when provider is `ollama` |
| `VECTOR_COLLECTION` | `digemid` | `pgvector` collection name |
| `RETRIEVAL_MAX_DISTANCE` | `0.7` | Max cosine distance |
| `RETRIEVAL_MAX_RESULTS` | `12` | Max returned chunks |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Reverse-proxy subnet in production |
| `LANGSMITH_TRACING` | `false` | Set `true` + `LANGSMITH_API_KEY` for nested traces |

> Changing embedding dimensions requires a schema migration and a full reindex.

## Data Pipeline

```bash
uv run ingest-digemid                     # Download DIGEMID PDFs & index pending docs
uv run python -m app.scripts.index_to_rag # Index pending docs only
uv run reindex-embeddings --yes           # Clear collection vectors & mark docs pending
```

## Tests

```bash
uv run pytest -q
```

Keep `uv.lock` in sync with `pyproject.toml` (Docker builds use `uv sync --frozen`).
