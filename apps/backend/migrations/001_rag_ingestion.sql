create extension if not exists vector with schema extensions;

create schema if not exists rag;
revoke all on schema rag from public;
revoke all on schema rag from anon, authenticated;

create table if not exists rag.embedding_config (
    id boolean primary key default true check (id),
    model text not null check (length(trim(model)) > 0),
    embedding_dimension integer not null check (embedding_dimension > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

insert into rag.embedding_config (id, model, embedding_dimension)
values (true, 'embeddinggemma', 768)
on conflict (id) do nothing;

create table if not exists rag.documents (
    id bigint generated always as identity primary key,
    collection text not null check (length(trim(collection)) > 0),
    doc_hash text not null check (doc_hash ~ '^[0-9a-f]{64}$'),
    source_url text,
    filename text not null,
    storage_key text not null,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'indexed', 'failed')),
    retries integer not null default 0 check (retries >= 0),
    last_error text,
    parser_version text,
    raw_text text,
    indexed_at timestamptz,
    lease_owner text,
    lease_until timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (collection, doc_hash),
    unique (collection, storage_key)
);

create index if not exists documents_claim_idx
    on rag.documents (collection, status, lease_until, created_at);

create table if not exists rag.chunks (
    id bigint generated always as identity primary key,
    document_id bigint not null references rag.documents (id) on delete cascade,
    chunk_index integer not null check (chunk_index >= 0),
    chunk_hash text not null check (chunk_hash ~ '^[0-9a-f]{64}$'),
    chunk_text text not null check (length(trim(chunk_text)) > 0),
    metadata jsonb not null default '{}'::jsonb,
    embedding extensions.vector(768) not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (document_id, chunk_index),
    unique (document_id, chunk_hash)
);

create index if not exists chunks_document_id_idx on rag.chunks (document_id);

alter table rag.embedding_config enable row level security;
alter table rag.documents enable row level security;
alter table rag.chunks enable row level security;

revoke all on all tables in schema rag from public;
revoke all on all tables in schema rag from anon, authenticated;
revoke all on all sequences in schema rag from public;
revoke all on all sequences in schema rag from anon, authenticated;

revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
