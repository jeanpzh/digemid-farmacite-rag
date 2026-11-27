from langchain_aws import ChatBedrockConverse
from langchain_groq import ChatGroq

from app.settings import Settings, settings


def create_model(config: Settings = settings):
    if config.chat_provider == "bedrock":
        return ChatBedrockConverse(
            model=config.model_name,
            region_name=config.aws_region,
            credentials_profile_name=config.aws_profile,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    if config.chat_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=config.model_name,
            base_url=config.ollama_base_url,
            temperature=config.temperature,
        )
    return ChatGroq(
        model=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        reasoning_format=config.reasoning_format,
        reasoning_effort=config.reasoning_effort,
    )


def create_router_model(config: Settings = settings):
    provider = config.resolved_router_provider
    if provider == "bedrock":
        return ChatBedrockConverse(
            model=config.router_model_name,
            region_name=config.aws_region,
            credentials_profile_name=config.aws_profile,
            temperature=0,
            max_tokens=config.router_max_tokens,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=config.router_model_name,
            base_url=config.ollama_base_url,
            temperature=0,
        )
    return ChatGroq(
        model=config.router_model_name,
        temperature=0,
        max_tokens=config.router_max_tokens,
    )


def create_judge_model(config: Settings = settings):
    provider = config.resolved_eval_provider
    if provider == "bedrock":
        return ChatBedrockConverse(
            model=config.eval_judge_model,
            region_name=config.aws_region,
            credentials_profile_name=config.aws_profile,
            temperature=0,
            max_tokens=config.eval_judge_max_tokens,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=config.eval_judge_model,
            base_url=config.ollama_base_url,
            temperature=0,
        )
    return ChatGroq(
        model=config.eval_judge_model,
        temperature=0,
        max_tokens=config.eval_judge_max_tokens,
    )
