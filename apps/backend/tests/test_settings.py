import pytest
from pydantic import ValidationError

from app.settings import Settings


def settings(**overrides):
    return Settings(
        supabase_db_url="postgresql://example.test/db",
        **overrides,
    )


def test_embedding_dimension_accepts_environment_string_for_current_schema():
    assert settings(embedding_dimension="1024").embedding_dimension == 1024


def test_embedding_dimension_rejects_values_other_than_current_schema():
    with pytest.raises(ValidationError, match="EMBEDDING_DIMENSION"):
        settings(embedding_dimension=768)


def test_bedrock_embedding_provider_requires_aws_region():
    with pytest.raises(ValidationError, match="AWS_REGION"):
        settings(embedding_provider="bedrock", aws_region="   ")


def test_default_embedding_configuration_uses_bedrock_titan_v2():
    configured = settings()
    assert configured.embedding_provider == "bedrock"
    assert configured.embedding_model == "amazon.titan-embed-text-v2:0"
    assert configured.embedding_dimension == 1024
    assert configured.aws_region == "us-east-2"


def test_groq_requires_an_api_key():
    with pytest.raises(ValidationError, match="GROQ_API_KEY"):
        settings(chat_provider="groq", groq_api_key="")


def test_production_accepts_groq_configuration():
    configured = settings(
        environment="production",
        chat_provider="groq",
        groq_api_key="groq-key",
    )

    assert configured.chat_provider == "groq"


def test_bedrock_chat_provider_does_not_require_groq_api_key():
    configured = settings(
        chat_provider="bedrock",
        model_name="us.amazon.nova-lite-v1:0",
        router_model_name="us.amazon.nova-micro-v1:0",
        groq_api_key="",
    )

    assert configured.chat_provider == "bedrock"
    assert configured.resolved_router_provider == "bedrock"
    assert configured.router_model_name == "us.amazon.nova-micro-v1:0"
