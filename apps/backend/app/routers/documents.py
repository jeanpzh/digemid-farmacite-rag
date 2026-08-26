from typing import Annotated

from app.dependencies.document_files import get_document_file_service
from app.services.document_files import DocumentFileService, DocumentNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}/pdf", summary="Render a source PDF")
async def get_document_pdf(
    document_id: int,
    version: Annotated[str, Query(min_length=1, max_length=200)],
    document_files: DocumentFileService = Depends(get_document_file_service),
):
    try:
        pdf_url = await document_files.get_pdf_url(document_id, version)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Document PDF not found") from error

    return RedirectResponse(
        url=pdf_url,
        status_code=307,
        headers={"Cache-Control": "private, max-age=60"},
    )
