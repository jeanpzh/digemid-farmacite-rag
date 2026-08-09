"""Prompt templates used by the RAG pipeline."""

from langchain_core.prompts import PromptTemplate

MULTI_QUERY_TEMPLATE = """You are an AI language model assistant. Your task is to generate {query_count}
different versions of the given user question to retrieve relevant documents from a vector
Provide these alternative questions separated by newlines. Original question: {question}"""

MULTI_QUERY_PROMPT = PromptTemplate.from_template(MULTI_QUERY_TEMPLATE)

ANSWER_PROMPT = PromptTemplate.from_template(
    """Answer the question using only the provided sources.
If the sources do not contain the answer, say that you do not know.
Every factual statement must include one or more source identifiers such as [S1].
Do not invent source identifiers.

Question: {question}

Sources:
{sources}
"""
)
