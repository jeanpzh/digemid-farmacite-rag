alter table rag.langchain_embeddings enable row level security;

revoke all on rag.langchain_embeddings from public, anon, authenticated;
