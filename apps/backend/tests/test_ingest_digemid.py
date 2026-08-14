import pytest

from app.scripts import ingest_digemid


def test_ingest_digemid_downloads_before_indexing(monkeypatch):
    calls = []

    monkeypatch.setattr(
        ingest_digemid,
        "bulk_download_pdfs",
        lambda: calls.append("download") or ["first.pdf", "second.pdf"],
    )
    monkeypatch.setattr(
        ingest_digemid,
        "index_pending_documents",
        lambda: calls.append("index") or 2,
    )

    indexed = ingest_digemid.ingest_digemid()

    assert calls == ["download", "index"]
    assert indexed == 2


def test_ingest_digemid_does_not_index_when_download_fails(monkeypatch):
    def fail_download():
        raise RuntimeError("download failed")

    monkeypatch.setattr(ingest_digemid, "bulk_download_pdfs", fail_download)
    monkeypatch.setattr(
        ingest_digemid,
        "index_pending_documents",
        lambda: pytest.fail("indexing must not run after a download failure"),
    )

    with pytest.raises(RuntimeError, match="download failed"):
        ingest_digemid.ingest_digemid()


def test_ingest_digemid_propagates_indexing_failures(monkeypatch):
    monkeypatch.setattr(ingest_digemid, "bulk_download_pdfs", lambda: [])

    def fail_indexing():
        raise RuntimeError("indexing failed")

    monkeypatch.setattr(ingest_digemid, "index_pending_documents", fail_indexing)

    with pytest.raises(RuntimeError, match="indexing failed"):
        ingest_digemid.ingest_digemid()
