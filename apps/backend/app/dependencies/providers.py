from fastapi import Request
from app.services.chat import ChatService

def get_chat_service(
    request: Request,
) -> ChatService:
    return request.app.state.chat_service
