import asyncio
import logging
from datetime import date
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, HttpUrl

from app.routers.chat import limiter
from app.services import document_library
from app.settings import settings

logger = logging.getLogger(__name__)


def require_library(request: Request) -> None:
    if not settings.source_library_enabled:
        raise HTTPException(404)
    if request.method != "GET" and request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403)


router = APIRouter(
    prefix="/source-library",
    tags=["sources"],
    dependencies=[Depends(require_library)],
)


class PublishSource(BaseModel):
    replaces_id: int | None = None
    source_url: HttpUrl | None = None
    effective_on: date | None = None


@router.get("")
def get_sources(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"documents": document_library.list_documents()}


@router.post("/uploads")
@limiter.limit("20/minute")
async def upload_source(
    request: Request, response: Response, filename: Annotated[str, Query(min_length=1, max_length=240)]
):
    name = PurePosixPath(filename.replace("\\", "/")).name.strip()
    if request.headers.get("content-type") != "application/pdf" or not name.lower().endswith(".pdf"):
        raise HTTPException(415, "Selecciona un archivo PDF.")
    data = bytearray()
    async for part in request.stream():
        if len(data) + len(part) > document_library.MAX_UPLOAD_BYTES:
            raise HTTPException(413, "El PDF supera el límite de 8 MB.")
        data.extend(part)
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "El archivo no tiene un encabezado PDF válido.")
    try:
        return await asyncio.to_thread(document_library.store_upload, bytes(data), name)
    except Exception:
        logger.exception("Source upload failed")
        raise HTTPException(502, "No se pudo guardar el PDF. Inténtalo de nuevo.") from None


@router.post("/{document_id}/retry", status_code=204)
def retry_source(document_id: int) -> None:
    try:
        document_library.retry_document(document_id)
    except document_library.LibraryConflict as error:
        raise HTTPException(409, str(error)) from error


@router.post("/{document_id}/publish", status_code=204)
def publish_source(document_id: int, payload: PublishSource) -> None:
    try:
        document_library.publish_document(
            document_id,
            replaces_id=payload.replaces_id,
            source_url=str(payload.source_url) if payload.source_url else None,
            effective_on=payload.effective_on,
        )
    except document_library.LibraryConflict as error:
        raise HTTPException(409, str(error)) from error
