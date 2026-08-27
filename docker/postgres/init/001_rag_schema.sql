CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.embedding_config (
    id boolean PRIMARY KEY DEFAULT true CHECK (id),
    model text NOT NULL CHECK (length(trim(model)) > 0),
    embedding_dimension integer NOT NULL CHECK (embedding_dimension > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO rag.embedding_config (id, model, embedding_dimension)
VALUES (true, 'embeddinggemma', 768)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS rag.documents (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collection text NOT NULL CHECK (length(trim(collection)) > 0),
    doc_hash text NOT NULL CHECK (doc_hash ~ '^[0-9a-f]{64}$'),
    source_url text,
    filename text NOT NULL,
    storage_key text NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'indexed', 'failed')),
    retries integer NOT NULL DEFAULT 0 CHECK (retries >= 0),
    last_error text,
    parser_version text,
    raw_text text,
    indexed_at timestamptz,
    lease_owner text,
    lease_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (collection, doc_hash),
    UNIQUE (collection, storage_key)
);

CREATE INDEX IF NOT EXISTS documents_claim_idx
    ON rag.documents (collection, status, lease_until, created_at);

CREATE TABLE IF NOT EXISTS rag.langchain_embeddings (
    langchain_id text PRIMARY KEY,
    content text NOT NULL,
    embedding vector(768) NOT NULL,
    collection text,
    doc_hash text,
    page integer,
    start_index integer,
    langchain_metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS langchain_embeddings_collection_doc_hash_idx
    ON rag.langchain_embeddings (collection, doc_hash);
