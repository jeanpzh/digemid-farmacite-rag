import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies.document_files import get_document_file_service
from app.routers.documents import router
from app.services.document_files import DocumentFileService
from app.services.document_files import DocumentNotFoundError


class FakeDocumentFileService:
    def __init__(self, pdf_url: str | None = None):
        self.pdf_url = pdf_url

    async def get_pdf_url(self, document_id: int, document_version: str) -> str:
        if self.pdf_url is None:
            raise DocumentNotFoundError(document_id, document_version)
        return self.pdf_url


class FakeResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, _statement):
        return FakeResult(self.row)


class FakeEngine:
    def __init__(self, row):
        self.row = row

    def connect(self):
        return FakeConnection(self.row)


class FakeStorageBucket:
    def __init__(self):
        self.signed_key = None
        self.signed_expiry = None

    def from_(self, _bucket):
        return self

    def create_signed_url(self, storage_key, expires_in):
        self.signed_key = storage_key
        self.signed_expiry = expires_in
        return {
            "signedURL": (
                "https://project.supabase.co/storage/v1/object/sign/"
                "documents/digemid/hash.pdf?token=test"
            )
        }


class FakeStorageClient:
    def __init__(self):
        self.storage = FakeStorageBucket()


def create_client(service: FakeDocumentFileService) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_document_file_service] = lambda: service
    return TestClient(app)


def test_document_file_service_creates_signed_url_for_storage_key():
    storage = FakeStorageClient()
    service = DocumentFileService(
        metadata_engine=FakeEngine({"storage_key": "digemid/hash.pdf"}),
        storage_client_factory=lambda: storage,
    )

    pdf_url = asyncio.run(service.get_pdf_url(42, "hash"))

    assert pdf_url.endswith("documents/digemid/hash.pdf?token=test")
    assert storage.storage.signed_key == "digemid/hash.pdf"
    assert storage.storage.signed_expiry == 300


def test_document_pdf_endpoint_redirects_to_signed_pdf_url():
    signed_url = "https://project.supabase.co/storage/v1/object/sign/documents/test.pdf?token=test"
    service = FakeDocumentFileService(pdf_url=signed_url)

    with create_client(service) as client:
        response = client.get(
            "/api/v1/documents/42/pdf",
            params={"version": "abc123"},
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert response.headers["location"] == signed_url
    assert response.headers["cache-control"] == "private, max-age=60"


def test_document_pdf_endpoint_returns_not_found_for_missing_document():
    with create_client(FakeDocumentFileService()) as client:
        response = client.get(
            "/api/v1/documents/42/pdf",
            params={"version": "missing"},
        )

    assert response.status_code == 404
