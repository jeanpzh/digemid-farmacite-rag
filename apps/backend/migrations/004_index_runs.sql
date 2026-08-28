create schema if not exists rag;

create table if not exists rag.index_runs (
    run_id uuid primary key,
    collection text not null check (length(trim(collection)) > 0),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null check (status in ('running', 'paused', 'completed', 'failed', 'cancelled')),
    metrics jsonb not null default '{}'::jsonb
);

create index if not exists index_runs_collection_started_at_idx
    on rag.index_runs (collection, started_at desc);

alter table rag.index_runs enable row level security;

revoke all on rag.index_runs from public;
