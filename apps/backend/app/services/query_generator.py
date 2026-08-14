from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.configs.prompts import MULTI_QUERY_PROMPT
from app.settings import settings

class QueryGenerator:
    def __init__(self, model,  query_generator_template : PromptTemplate = MULTI_QUERY_PROMPT ):
        self.query_generator_template = query_generator_template
        self.model = model

    async def generate_queries(self, question: str, history: str = "") -> list[str]:
        chain = (
            self.query_generator_template
            | self.model
            | StrOutputParser()
            | (lambda x: x.split("\n"))
        )

        result = await chain.ainvoke({
            "question": question,
            "history": history,
            "query_count": settings.query_count,
        })
        queries = []
        for query in result:
            normalized = query.strip().lstrip("-•")
            if normalized[:2].rstrip(".").isdigit():
                normalized = normalized[2:].lstrip(". ")
            if normalized and normalized not in queries:
                queries.append(normalized)
        return queries[: settings.query_count]
