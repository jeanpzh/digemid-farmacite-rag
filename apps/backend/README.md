# Backend Reference

For project setup, Docker, API usage, citations, and LangSmith tracing, see the
[repository README](../../README.md). This document only covers backend-specific
implementation details and maintenance commands.

## Code Boundaries

- `app/configs/scrapy_digemid.py`: downloads source PDFs and records their source metadata.
- `app/services/langchain_indexer.py`: parses PDFs, creates chunks, embeds them with Ollama, and writes vectors.
- `app/services/multiquery_retriever.py`: expands questions, searches pgvector, and enriches chunks with source metadata.
- `app/services/rag_query.py`: builds the grounded answer and structured citations.
- `app/scripts/index_to_rag.py`: claims pending documents and runs indexing with leases.
- `app/db.py`: owns the synchronous SQLAlchemy pool and advisory lock.
- `migrations/`: defines the `rag` schema, vector table, and RLS policies.

## Data Contract

`rag.documents` stores one source row per PDF:

- `doc_hash`: content identity and vector join key.
- `source_url`: public origin URL.
- `filename`: display name for citations.
- `storage_key`: private Supabase Storage path.
- `status`, `lease_owner`, and `lease_until`: indexing state.

`rag.langchain_embeddings` stores one row per chunk:

- `langchain_id`: deterministic chunk ID.
- `content`: extracted chunk text.
- `collection` and `doc_hash`: source relationship.
- `page` and `start_index`: page-local chunk location.
- `langchain_metadata`: PDF metadata such as page label and total pages.

The retriever joins these records by `collection` and `doc_hash` before the
answer chain runs. It adds `filename`, `source_url`, `storage_key`, and
`end_index` to each LangChain document.

## Maintenance Commands

Run from `apps/backend`:

```bash
uv sync --frozen
uv run python -m app.scripts.downloader
uv run python -m app.scripts.index_to_rag
uv run ingest-digemid
uv run reindex-embeddings --yes
```

The reindex command deletes vectors for the selected collection and resets
documents to `pending`. It requires `--yes` intentionally.

## Connection Pools

The API uses a bounded synchronous SQLAlchemy pool for document state. Each
pgvector request creates a temporary async `PGEngine` with one connection and
zero overflow, then closes it in a `finally` block. If a process was running an
older build that leaked sessions, restart the API container:

```bash
docker compose restart app
```

Do not increase pool sizes without checking the Supabase session-mode limit and
the number of application workers.

## Indexing Semantics

The indexer claims one pending document at a time with a lease. A failed item is
marked `failed` and can be retried until its retry limit. A successful item is
marked `indexed` only after its chunks and embeddings have been written.
