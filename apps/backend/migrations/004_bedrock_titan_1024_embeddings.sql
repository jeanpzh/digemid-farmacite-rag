truncate table rag.langchain_embeddings;

alter table rag.langchain_embeddings
    alter column embedding type extensions.vector(1024);

update rag.documents
set status = 'pending',
    retries = 0,
    last_error = null,
    parser_version = null,
    indexed_at = null,
    lease_owner = null,
    lease_until = null,
    updated_at = now();

update rag.embedding_config
set model = 'amazon.titan-embed-text-v2:0',
    embedding_dimension = 1024,
    updated_at = now()
where id is true;
