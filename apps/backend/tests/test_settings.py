import pytest
from pydantic import ValidationError

from app.settings import Settings


def settings(**overrides):
    return Settings(
        supabase_db_url="postgresql://example.test/db",
        **overrides,
    )


def test_embedding_dimension_accepts_environment_string_for_current_schema():
    assert settings(embedding_dimension="768").embedding_dimension == 768


def test_embedding_dimension_rejects_values_other_than_current_schema():
    with pytest.raises(ValidationError, match="EMBEDDING_DIMENSION"):
        settings(embedding_dimension=1536)


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
