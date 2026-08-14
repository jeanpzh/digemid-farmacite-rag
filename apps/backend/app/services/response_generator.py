from app.configs.prompts import ANSWER_PROMPT
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
class ResponseGenerator:
    def __init__(self, model):
        self.model = model

    async def stream(
        self,
        question: str,
        history: str,
        sources: str,
        prompt : PromptTemplate = ANSWER_PROMPT,
    ):
        chain = (
            prompt
            | self.model
            | StrOutputParser()
        )

        async for chunk in chain.astream({
            "question": question,
            "history": history,
            "sources": sources,
        }):
            yield chunk
