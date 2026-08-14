from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.dependencies.providers import get_chat_service
from app.routers.chat import limiter, router
from app.schemas.chat_events import RetrievalStatusChanged, TextDelta


class FakeChatService:
    def stream(self, _messages) -> AsyncIterator:
        async def events():
            yield RetrievalStatusChanged(state="active", label="Buscando fuentes relevantes")
            yield TextDelta(text="respuesta")

        return events()


def chat_payload() -> dict:
    return {
        "messages": [
            {
                "id": "user-1",
                "role": "user",
                "parts": [{"type": "text", "text": "pregunta"}],
            }
        ],
        "requestId": "request-1",
    }


def create_client(client_ip: str = "testclient") -> TestClient:
    app = FastAPI()
    app.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts="172.16.0.0/12",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(router)
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    return TestClient(app, client=(client_ip, 50000))


def test_chat_endpoint_returns_ephemeral_ai_sdk_stream():
    limiter.reset()
    with create_client() as client:
        response = client.post("/chat", json=chat_payload())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "text-delta"' in response.text


def test_chat_rejects_the_eleventh_request_from_one_ip():
    limiter.reset()

    with create_client("203.0.113.10") as client:
        responses = [
            client.post(
                "/chat",
                headers={"X-Forwarded-For": f"198.51.100.{index}"},
                json=chat_payload(),
            )
            for index in range(11)
        ]

    assert [response.status_code for response in responses[:10]] == [200] * 10
    assert responses[10].status_code == 429
    assert responses[10].headers["retry-after"] == "60"


def test_chat_rate_limit_is_independent_per_ip():
    limiter.reset()

    with create_client("203.0.113.10") as client:
        for _ in range(10):
            assert client.post(
                "/chat",
                json=chat_payload(),
            ).status_code == 200

    with create_client("203.0.113.11") as client:
        response = client.post(
            "/chat",
            json=chat_payload(),
        )

    assert response.status_code == 200


def test_chat_uses_the_client_ip_forwarded_by_traefik():
    limiter.reset()

    with create_client("172.18.0.2") as client:
        for index in range(10):
            assert client.post(
                "/chat",
                headers={"X-Forwarded-For": f"198.51.100.{index}, 203.0.113.10"},
                json=chat_payload(),
            ).status_code == 200

        other_client = client.post(
            "/chat",
            headers={"X-Forwarded-For": "203.0.113.11"},
            json=chat_payload(),
        )
        response = client.post(
            "/chat",
            headers={"X-Forwarded-For": "198.51.100.99, 203.0.113.10"},
            json=chat_payload(),
        )

    assert other_client.status_code == 200
    assert response.status_code == 429
