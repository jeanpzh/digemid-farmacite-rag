import glob
import os

from scrapy.crawler import CrawlerProcess

from app.configs.scrapy_digemid import DIGEMID_SETTINGS, DigemidPdfSpider, PDF_STORE_DIR

def bulk_download_pdfs(files_store: str | None = None) -> list[str]:
    """ 
    Download all PDFs from the Digemid website using Scrapy and return a list of file paths.
    
    Args:
        files_store (str | None): The directory to store the downloaded files. If None, the default directory will be used.

    Returns:
        list[str]: A list of file paths for the downloaded PDFs.
    """
    settings = dict(DIGEMID_SETTINGS)
    if files_store:
        settings["FILES_STORE"] = os.path.abspath(files_store)
    os.makedirs(settings["FILES_STORE"], exist_ok=True)

    process = CrawlerProcess(settings)
    process.crawl(DigemidPdfSpider)
    process.start()

    store = settings["FILES_STORE"]
    return sorted(glob.glob(os.path.join(store, "**", "*.pdf"), recursive=True))


if __name__ == "__main__":
    pdfs = bulk_download_pdfs()
    print(f"Downloaded {len(pdfs)} PDFs to {os.path.abspath(PDF_STORE_DIR)}")
