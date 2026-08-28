from fastapi import Request

from app.services.indexing_jobs import IndexingJobService


def get_indexing_service(request: Request) -> IndexingJobService:
    return request.app.state.indexing_service
