from langchain_postgres import PGVectorStore
from app.settings import settings

def create_vector_store(embedding_service, engine) -> PGVectorStore:
    return PGVectorStore.create_sync(
        engine=engine,
        embedding_service= embedding_service,
        schema_name=settings.schema_name,
        table_name=settings.table_name,
        metadata_columns=list(settings.metadata_columns),
    )
