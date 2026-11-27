create index if not exists langchain_embeddings_embedding_hnsw_idx
    on rag.langchain_embeddings
    using hnsw (embedding extensions.vector_cosine_ops);
