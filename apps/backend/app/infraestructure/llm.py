from app.settings import settings
from langchain_groq import ChatGroq


def create_model():
    if settings.chat_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.model_name,
            base_url=settings.ollama_base_url,
            temperature=settings.temperature,
        )
    return ChatGroq(
        model=settings.model_name,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        reasoning_format=settings.reasoning_format,
        reasoning_effort=settings.reasoning_effort,
    )
