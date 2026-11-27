from langchain_aws import BedrockEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from app.settings import Settings, settings


def create_embedding_service(config: Settings = settings) -> Embeddings:
    if config.embedding_provider == "bedrock":
        return BedrockEmbeddings(
            model_id=config.embedding_model,
            region_name=config.aws_region,
            credentials_profile_name=config.aws_profile,
            dimensions=config.embedding_dimension,
            normalize=True,
        )
    if config.embedding_provider == "ollama":
        return OllamaEmbeddings(
            model=config.embedding_model,
            base_url=config.ollama_base_url,
        )
    raise ValueError(f"Unsupported embedding provider: {config.embedding_provider}")
