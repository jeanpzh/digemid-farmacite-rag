from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VECTOR_SCHEMA = "rag"
VECTOR_TABLE = "langchain_embeddings"
DEFAULT_EMBEDDING_MODEL = "embeddinggemma"
ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
ReasoningFormat = Literal["hidden", "parsed", "raw"]
ChatProvider = Literal["groq", "ollama"]
StorageBackend = Literal["supabase", "s3"]
Environment = Literal["development", "production"]

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        frozen=True,
        extra="ignore",
    )
    model_name : str = "qwen/qwen3.6-27b"
    supabase_db_url: str = Field(...)
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimension: int = 768
    chat_provider: ChatProvider = "groq"
    environment: Environment = "development"
    groq_api_key: str | None = None
    reasoning_format: ReasoningFormat = "hidden"
    reasoning_effort: str = "none"
    temperature: float = 0
    max_tokens: int = 4096
    table_name: str = VECTOR_TABLE
    schema_name: str = VECTOR_SCHEMA
    vector_collection: str = "digemid"
    storage_backend: StorageBackend = "supabase"
    storage_bucket: str = Field(
        default="documents",
        validation_alias=AliasChoices("STORAGE_BUCKET", "SUPABASE_STORAGE_BUCKET"),
    )
    s3_endpoint_url: str | None = None
    s3_public_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    metadata_columns: list[str] = [
        "collection",
        "doc_hash",
        "page",
        "start_index",
    ]
    db_pool_min_size: int = 1
    db_pool_max_size: int = 4
    db_pool_timeout: float = 30.0
    query_count: int = 5
    retrieval_max_distance: float = Field(default=0.7, ge=0)
    retrieval_max_results: int = Field(default=12, ge=1)
    ollama_base_url: str = "http://localhost:11434"

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        if self.embedding_dimension != 768:
            raise ValueError("EMBEDDING_DIMENSION must be 768 for the current vector schema")
        if self.chat_provider == "groq" and not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when CHAT_PROVIDER=groq")
        if self.storage_backend == "s3" and not self.s3_endpoint_url:
            raise ValueError("S3_ENDPOINT_URL is required when STORAGE_BACKEND=s3")
        return self


settings = Settings()   # type: ignore[call-arg]
