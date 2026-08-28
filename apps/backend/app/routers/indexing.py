from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.indexing import get_indexing_service
from app.schemas.indexing import IndexingRunRead, IndexingRunStartRequest
from app.services.indexing_jobs import (
    ActiveIndexingRunError,
    IndexingJobNotFoundError,
    IndexingJobService,
)


router = APIRouter(prefix="/indexing", tags=["indexing"])
Service = Annotated[IndexingJobService, Depends(get_indexing_service)]


@router.post(
    "/runs",
    response_model=IndexingRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_indexing_run(payload: IndexingRunStartRequest, service: Service):
    try:
        return service.start(payload.collection, payload.mode)
    except ActiveIndexingRunError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/runs/latest", response_model=IndexingRunRead | None)
def get_latest_indexing_run(
    service: Service,
    collection: Annotated[str, Query(min_length=1, max_length=120)] = "digemid",
):
    return service.get_latest(collection)


@router.get("/runs/{run_id}", response_model=IndexingRunRead)
def get_indexing_run(run_id: UUID, service: Service):
    try:
        return service.get_status(run_id)
    except IndexingJobNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _control_run(run_id: UUID, service: Service, action: str):
    try:
        return getattr(service, action)(run_id)
    except IndexingJobNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/runs/{run_id}/pause", response_model=IndexingRunRead)
def pause_indexing_run(run_id: UUID, service: Service):
    return _control_run(run_id, service, "pause")


@router.post("/runs/{run_id}/resume", response_model=IndexingRunRead)
def resume_indexing_run(run_id: UUID, service: Service):
    return _control_run(run_id, service, "resume")


@router.post("/runs/{run_id}/cancel", response_model=IndexingRunRead)
def cancel_indexing_run(run_id: UUID, service: Service):
    return _control_run(run_id, service, "cancel")
