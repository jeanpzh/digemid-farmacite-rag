from langchain_ollama import OllamaEmbeddings
from app.settings import settings


def create_embedding_service():
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
