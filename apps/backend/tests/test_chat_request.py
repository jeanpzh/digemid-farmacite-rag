from uuid import UUID

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from app.adapters.vercel_request import to_langchain_messages
from app.schemas.conversation import ChatRequest


def _message(text: str, message_id: str = "user-1", role: str = "user"):
    return {
        "id": message_id,
        "role": role,
        "parts": [{"type": "text", "text": text}],
    }


def test_chat_request_accepts_recent_conversation_history():
    conversation_id = "7f8f7a54-1fd4-4b35-a6ac-d5f3ab6e13f8"

    request = ChatRequest(
        conversationId=conversation_id,
        requestId="request-1",
        messages=[
            _message("pregunta inicial"),
            _message("respuesta", "assistant-1", "assistant"),
            _message("pregunta", "user-2"),
        ],
    )

    assert request.conversation_id == UUID(conversation_id)
    assert request.message.id == "user-2"
    assert request.message.text == "pregunta"
    assert to_langchain_messages(request.messages) == [
        HumanMessage(content="pregunta inicial"),
        AIMessage(content="respuesta"),
        HumanMessage(content="pregunta"),
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"requestId": "request-1", "messages": []},
        {"requestId": "request-1", "messages": [_message("   ")]},
        {"requestId": "request-1", "messages": [_message("respuesta", role="assistant")]},
        {
            "requestId": "request-1",
            "messages": [{"id": "user-1", "role": "user", "parts": []}],
        },
    ],
)
def test_chat_request_rejects_invalid_messages(payload):
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(payload)
