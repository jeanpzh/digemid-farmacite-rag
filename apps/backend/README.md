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
| `app/infraestructure/llm.py` | Chat & router LLM factories (`bedrock`, `groq`, or `ollama`) |
| `app/services/query_router.py` | Structured LLM router (`QueryRoute`: standalone query, medicines, intent) |
| `app/services/_multiquery_retriever.py` | Deterministic 1-search + capped adaptive expansion policy |
| `app/services/chat.py` | Retrieval, citations & answer streaming orchestration |
| `app/services/vector_retriever.py` | `pgvector` search & TTL-cached collection metadata enrichment |
| `app/services/langchain_indexer.py` | PDF parsing, chunking, embeddings & vector writes |
| `app/scripts/` | Ingestion, indexing & reindex CLIs |
| `app/settings.py` | Pydantic runtime config & fail-fast validation |

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `SUPABASE_DB_URL` | *(required)* | PostgreSQL connection string |
| `CHAT_PROVIDER` | `groq` | `bedrock`, `groq`, or `ollama` |
| `GROQ_API_KEY` | — | Required when chat or router uses `groq` |
| `MODEL_NAME` | `qwen/qwen3.6-27b` | Chat model ID (e.g., `us.amazon.nova-lite-v1:0` on Bedrock) |
| `ROUTER_PROVIDER` | *(inherits `CHAT_PROVIDER`)* | `bedrock`, `groq`, or `ollama` |
| `ROUTER_MODEL_NAME` | `us.amazon.nova-micro-v1:0` | Fast structured router model ID |
| `EMBEDDING_PROVIDER` | `bedrock` | `bedrock` or `ollama` |
| `EMBEDDING_MODEL` | `amazon.titan-embed-text-v2:0` | Embedding model ID |
| `EMBEDDING_DIMENSION` | `1024` | Must match `rag.langchain_embeddings` (`vector(1024)`) |
| `AWS_REGION` | `us-east-2` | Required when embeddings, chat, or router uses `bedrock` |
| `AWS_PROFILE` | — | Local AWS profile; omit in prod to use IAM role |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Used when provider is `ollama` |
| `VECTOR_COLLECTION` | `digemid` | `pgvector` collection name |
| `RETRIEVAL_MAX_DISTANCE` | `0.7` | Max cosine distance |
| `RETRIEVAL_MIN_RESULTS` | `3` | Min passing hits before adaptive expansion triggers |
| `RETRIEVAL_MAX_RESULTS` | `12` | Max returned chunks |
| `RETRIEVAL_EXPANSION_MAX_QUERIES` | `3` | Hard cap on targeted expansion queries (1 DB pool wave) |
| `METADATA_CACHE_TTL_SECONDS` | `300` | In-memory TTL cache for preloaded `rag.documents` metadata |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Reverse-proxy subnet in production |
| `LANGSMITH_TRACING` | `false` | Set `true` + `LANGSMITH_API_KEY` for nested traces |

> Changing embedding dimensions requires a schema migration and a full reindex.

## Retrieval Performance

Measured against Supabase `pgvector` (44 DIGEMID PDFs, 1,869 `vector(1024)` chunks) and AWS Bedrock (`us-east-2`):

| Stage | Before (always-expand 6 queries) | After (Bedrock router + adaptive + HNSW + cache) |
| --- | ---: | ---: |
| Postgres vector scan (`EXPLAIN ANALYZE`) | `227.3 ms` *(Seq Scan)* | **`3.95 ms`** *(HNSW Index Scan, **57× faster**)* |
| Metadata enrichment (`enrich_documents`) | `213.6 ms` | **`0.0 ms`** *(collection preload TTL cache)* |
| Total retrieval (over ~103 ms WAN RTT) | `1,942.7 ms` | **`838–848 ms`** *(**2.3× faster**)* |
| Bedrock answer streaming TTFT (`us.amazon.nova-lite-v1:0`) | — | **`208.8 ms`** |

> Note: `migrations/005_hnsw_cosine_index.sql` creates a table-wide HNSW index (`vector_cosine_ops`). If multiple large collections are added later, switch to partial HNSW indexes per collection or enable `hnsw.iterative_scan` to avoid post-filter recall starvation.

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
