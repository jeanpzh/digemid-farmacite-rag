from langchain_postgres import PGVectorStore

def create_vector_store(
    engine,
    embedding_service,
    schema_name,
    table_name,
    metadata_columns

):
    return PGVectorStore.create_sync(
        engine=engine,
        embedding_service=embedding_service,
        table_name=table_name,
        schema_name=schema_name,
        metadata_columns=metadata_columns
    )