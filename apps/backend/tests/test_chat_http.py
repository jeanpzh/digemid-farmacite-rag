from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies.providers import get_chat_service
from app.routers.chat import router
from app.schemas.chat_events import RetrievalStatusChanged, TextDelta


class FakeChatService:
    def stream(self, _messages) -> AsyncIterator:
        async def events():
            yield RetrievalStatusChanged(state="active", label="Buscando fuentes relevantes")
            yield TextDelta(text="respuesta")

        return events()


def test_chat_endpoint_returns_ephemeral_ai_sdk_stream():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "messages": [
                    {
                        "id": "user-1",
                        "role": "user",
                        "parts": [{"type": "text", "text": "pregunta"}],
                    }
                ],
                "requestId": "request-1",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "text-delta"' in response.text
