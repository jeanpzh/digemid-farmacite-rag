from hashlib import sha256
from pathlib import Path
from urllib.parse import unquote, urlparse

import scrapy
from scrapy.pipelines.files import FilesPipeline
from sqlalchemy.dialects.postgresql import insert
from app.models.document import Document
from app.db import session_scope
from app.services.document_storage import DocumentStorage, create_document_storage

BOT_NAME = "digemid"
SPIDER_NAME = "digemid_pdfs"
TARGET_PAGE = "https://www.digemid.minsa.gob.pe/webDigemid/registro-sanitario/productos-farmaceuticos/venta-sin-receta/"
PDF_STORE_DIR = str(Path(__file__).resolve().parents[2] / "data" / "digemid" / "pdfs")

DIGEMID_SETTINGS = {
    "BOT_NAME": BOT_NAME,
    "SPIDER_MODULES": ["app.configs.scrapy_digemid"],
    "NEWSPIDER_MODULE": "app.configs.scrapy_digemid",
    "USER_AGENT": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "DEFAULT_REQUEST_HEADERS": {
        "Referer": "https://www.digemid.minsa.gob.pe/webDigemid/",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    },
    "ROBOTSTXT_OBEY": False,
    "COOKIES_ENABLED": False,
    "DOWNLOAD_DELAY": 0.5,
    "CONCURRENT_REQUESTS": 8,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_TARGET_CONCURRENCY": 4.0,
    "AUTOTHROTTLE_START_DELAY": 1.0,
    "AUTOTHROTTLE_MAX_DELAY": 10.0,
    "RETRY_ENABLED": True,
    "RETRY_TIMES": 3,
    "RETRY_HTTP_CODES": [403, 429, 500, 502, 503, 504],
    "DOWNLOAD_TIMEOUT": 60,
    "DOWNLOAD_MAXSIZE": 50 * 1024 * 1024,
    "MEDIA_ALLOW_REDIRECTS": True,
    "FILES_STORE": PDF_STORE_DIR,
    "FILES_EXPIRES": 365,
    "ITEM_PIPELINES": {
        "app.configs.scrapy_digemid.DigemidFilesPipeline": 1,
        "app.configs.scrapy_digemid.DocumentStoragePipeline": 2,
    },
    "DOCUMENT_COLLECTION": "digemid",
    "LOG_LEVEL": "INFO",
}


class DigemidFilesPipeline(FilesPipeline):
    def file_path(self, request, response=None, info=None, *, item=None):
        filename = unquote(Path(request.url).name)
        key = sha256(request.url.encode("utf-8")).hexdigest()
        return f"{key}_{filename}"


class DocumentStoragePipeline:
    """Store completed downloads and queue them for the separate indexer."""

    def __init__(self, storage: DocumentStorage, files_store: Path, collection: str):
        self.storage = storage
        self.files_store = files_store.resolve()
        self.collection = collection
        self._storage_ready = False

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            create_document_storage(),
            Path(crawler.settings["FILES_STORE"]),
            crawler.settings["DOCUMENT_COLLECTION"],
        )

    def process_item(self, item, spider):
        for downloaded_file in item.get("files", []):
            if downloaded_file.get("status") not in {"downloaded", "uptodate"}:
                continue
            self._store_download(downloaded_file)
        return item

    def _store_download(self, downloaded_file: dict[str, str]) -> None:
        relative_path = Path(downloaded_file["path"])
        local_path = (self.files_store / relative_path).resolve()
        if not local_path.is_relative_to(self.files_store):
            raise ValueError("Downloaded file path must be inside FILES_STORE")

        contents = local_path.read_bytes()
        doc_hash = sha256(contents).hexdigest()
        storage_key = f"{self.collection}/{doc_hash}.pdf"
        source_url = downloaded_file["url"]
        filename = Path(unquote(urlparse(source_url).path)).name or local_path.name

        self._ensure_storage()
        self.storage.upload(
            storage_key,
            contents,
            content_type="application/pdf",
        )

        values = {
            "doc_hash": doc_hash,
            "source_url": source_url,
            "filename": filename,
            "storage_key": storage_key,
            "status": "pending",
            "collection": self.collection,
        }
        with session_scope() as session:
            session.execute(
                insert(Document)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["doc_hash", "collection"],
                    set_={
                        "source_url": source_url,
                        "filename": filename,
                        "storage_key": storage_key,
                    },
                )
            )
        local_path.unlink(missing_ok=True)

    def _ensure_storage(self) -> None:
        if self._storage_ready:
            return
        self.storage.ensure_bucket()
        self._storage_ready = True


class DigemidPdfSpider(scrapy.Spider):
    name = SPIDER_NAME
    start_urls = [TARGET_PAGE]

    def parse(self, response):
        seen = set()
        for href in response.xpath("//a[contains(@href, '.pdf')]/@href").getall():
            url = response.urljoin(href)
            if url in seen:
                continue
            seen.add(url)
            yield {"file_urls": [url]}
