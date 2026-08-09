drop table if exists rag.chunks;

create table if not exists rag.langchain_embeddings (
    langchain_id text primary key,
    content text not null,
    embedding extensions.vector(768) not null,
    collection text,
    doc_hash text,
    page integer,
    start_index integer,
    langchain_metadata jsonb not null default '{}'::jsonb
);

create index if not exists langchain_embeddings_collection_doc_hash_idx
    on rag.langchain_embeddings (collection, doc_hash);

revoke all on rag.langchain_embeddings from public, anon, authenticated;
