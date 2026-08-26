from fastapi import Request

from app.services.document_files import DocumentFileService


def get_document_file_service(request: Request) -> DocumentFileService:
    return request.app.state.document_file_service
