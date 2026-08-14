
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    BaseMessage,
)
from app.schemas.conversation import ConversationMessageInput

def to_langchain_messages(
    messages: list[ConversationMessageInput],
) -> list[BaseMessage]:

    result: list[BaseMessage] = []

    for message in messages:
        text = message.text

        if message.role == "user":
            result.append(HumanMessage(content=text))
        else:
            result.append(AIMessage(content=text))

    return result
