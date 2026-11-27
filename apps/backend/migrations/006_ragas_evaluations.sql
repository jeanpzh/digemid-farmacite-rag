create table if not exists rag.eval_runs (
    id bigint generated always as identity primary key,
    name text not null check (length(trim(name)) > 0),
    git_sha text,
    dataset_name text not null default 'digemid-golden-v1',
    chat_provider text not null,
    chat_model text not null,
    router_model text not null,
    embedding_model text not null,
    judge_model text not null,
    sample_count integer not null check (sample_count >= 0),
    avg_faithfulness double precision,
    avg_context_precision double precision,
    avg_context_recall double precision,
    avg_response_relevancy double precision,
    avg_retrieval_ms double precision,
    p95_retrieval_ms double precision,
    avg_ttft_ms double precision,
    refusal_accuracy double precision,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists eval_runs_created_at_idx
    on rag.eval_runs (created_at desc);

create table if not exists rag.eval_results (
    id bigint generated always as identity primary key,
    run_id bigint not null references rag.eval_runs (id) on delete cascade,
    case_id text not null,
    category text not null check (category in ('standalone', 'followup', 'multi_medicine', 'out_of_domain')),
    question text not null,
    history text not null default '',
    reference_answer text not null default '',
    generated_answer text not null,
    retrieved_contexts jsonb not null default '[]'::jsonb,
    faithfulness double precision,
    context_precision double precision,
    context_recall double precision,
    response_relevancy double precision,
    retrieval_ms double precision,
    ttft_ms double precision,
    passed_refusal boolean,
    claims jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists eval_results_run_id_idx
    on rag.eval_results (run_id, id);

alter table rag.eval_runs enable row level security;
alter table rag.eval_results enable row level security;

revoke all on rag.eval_runs from public, anon, authenticated;
revoke all on rag.eval_results from public, anon, authenticated;
revoke all on sequence rag.eval_runs_id_seq from public, anon, authenticated;
revoke all on sequence rag.eval_results_id_seq from public, anon, authenticated;
