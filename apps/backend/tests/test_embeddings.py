from app.infraestructure import embeddings as embeddings_module
from app.settings import Settings


def make_settings(**overrides) -> Settings:
    return Settings(
        supabase_db_url="postgresql://example.test/db",
        groq_api_key="test-groq-key",
        **overrides,
    )


def test_create_embedding_service_builds_bedrock_client(monkeypatch):
    captured = {}

    class FakeBedrockEmbeddings:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(embeddings_module, "BedrockEmbeddings", FakeBedrockEmbeddings)

    config = make_settings(
        embedding_provider="bedrock",
        embedding_model="amazon.titan-embed-text-v2:0",
        embedding_dimension=1024,
        aws_region="us-east-2",
        aws_profile="jeanpzh",
    )
    service = embeddings_module.create_embedding_service(config)

    assert isinstance(service, FakeBedrockEmbeddings)
    assert captured == {
        "model_id": "amazon.titan-embed-text-v2:0",
        "region_name": "us-east-2",
        "credentials_profile_name": "jeanpzh",
        "dimensions": 1024,
        "normalize": True,
    }


def test_create_embedding_service_builds_ollama_client(monkeypatch):
    captured = {}

    class FakeOllamaEmbeddings:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(embeddings_module, "OllamaEmbeddings", FakeOllamaEmbeddings)

    config = make_settings(
        embedding_provider="ollama",
        embedding_model="mxbai-embed-large",
        embedding_dimension=1024,
        ollama_base_url="http://localhost:11434",
    )
    service = embeddings_module.create_embedding_service(config)

    assert isinstance(service, FakeOllamaEmbeddings)
    assert captured == {
        "model": "mxbai-embed-large",
        "base_url": "http://localhost:11434",
    }
