from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VECTOR_SCHEMA = "rag"
VECTOR_TABLE = "langchain_embeddings"
DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_ROUTER_MODEL = "us.amazon.nova-micro-v1:0"
DEFAULT_EVAL_JUDGE_MODEL = "us.amazon.nova-2-lite-v1:0"
EMBEDDING_DIMENSION = 1024
ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
ReasoningFormat = Literal["hidden", "parsed", "raw"]
ChatProvider = Literal["bedrock", "groq", "ollama"]
EmbeddingProvider = Literal["bedrock", "ollama"]
Environment = Literal["development", "production"]

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        frozen=True,
        extra="ignore",
    )
    model_name : str = "qwen/qwen3.6-27b"
    router_provider: ChatProvider | None = None
    router_model_name: str = DEFAULT_ROUTER_MODEL
    router_max_tokens: int = 256
    eval_provider: ChatProvider | None = None
    eval_judge_model: str = DEFAULT_EVAL_JUDGE_MODEL
    eval_judge_max_tokens: int = 2048
    supabase_db_url: str = Field(...)
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    source_library_enabled: bool = False
    embedding_provider: EmbeddingProvider = "bedrock"
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimension: int = EMBEDDING_DIMENSION
    aws_region: str = "us-east-2"
    aws_profile: str | None = None
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
    retrieval_min_results: int = Field(default=3, ge=1)
    retrieval_max_results: int = Field(default=12, ge=1)
    retrieval_expansion_max_queries: int = Field(default=3, ge=1)
    metadata_cache_ttl_seconds: float = Field(default=300.0, ge=0.0)
    ollama_base_url: str = "http://localhost:11434"

    @property
    def resolved_router_provider(self) -> ChatProvider:
        return self.router_provider or self.chat_provider

    @property
    def resolved_eval_provider(self) -> ChatProvider:
        return self.eval_provider or self.resolved_router_provider

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        if self.embedding_dimension != EMBEDDING_DIMENSION:
            raise ValueError(
                f"EMBEDDING_DIMENSION must be {EMBEDDING_DIMENSION} for the current vector schema"
            )
        uses_bedrock = (
            self.embedding_provider == "bedrock"
            or self.chat_provider == "bedrock"
            or self.resolved_router_provider == "bedrock"
            or self.resolved_eval_provider == "bedrock"
        )
        if uses_bedrock and not self.aws_region.strip():
            raise ValueError("AWS_REGION is required when using Bedrock")
        uses_groq = (
            self.chat_provider == "groq"
            or self.resolved_router_provider == "groq"
            or self.resolved_eval_provider == "groq"
        )
        if uses_groq and not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when CHAT_PROVIDER=groq")
        return self


settings = Settings()   # type: ignore[call-arg]
