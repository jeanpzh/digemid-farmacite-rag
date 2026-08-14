from langchain_core.documents import Document

from app.schemas.chat_events import Citation
from app.services.citations import build_citations


def test_build_citations_preserves_source_metadata_and_normalizes_page():
    citations = build_citations(
        [
            Document(
                id="chunk-1",
                page_content="Contenido exacto.",
                metadata={
                    "filename": "norma.pdf",
                    "source_url": "https://example.test/norma.pdf",
                    "page": 2,
                    "page_label": "III",
                    "total_pages": 18,
                    "start_index": 10,
                    "end_index": 27,
                },
            )
        ]
    )

    assert citations == [
        Citation(
            id="cit_53395894eff55d9c",
            label="S1",
            source={
                "document_id": "unknown",
                "document_version": "unknown",
                "chunk_id": "chunk-1",
                "filename": "norma.pdf",
                "url": "https://example.test/norma.pdf",
            },
            location={
                "page": 3,
                "page_label": "III",
                "total_pages": 18,
                "start_index": 10,
                "end_index": 27,
            },
            excerpt="Contenido exacto.",
        )
    ]


def test_build_citations_uses_safe_defaults_for_missing_metadata():
    citations = build_citations(
        [Document(page_content="Texto")]
    )

    citation = citations[0]
    assert citation.source.chunk_id == "unknown"
    assert citation.label == "S1"
    assert citation.source.filename == "unknown"
    assert citation.location.page == 1
    assert citation.location.start_index == 0
    assert citation.location.end_index == 5


def test_build_citations_normalizes_malformed_optional_metadata():
    citation = build_citations(
        [
            Document(
                page_content="Texto",
                metadata={
                    "filename": None,
                    "source_url": 123,
                    "page_label": 4,
                    "total_pages": "not-a-number",
                },
            )
        ]
    )[0]

    assert citation.source.filename == "unknown"
    assert citation.source.url is None
    assert citation.location.page_label == "4"
    assert citation.location.total_pages is None


def test_build_citations_uses_stable_identity_and_bounds_excerpt():
    document = Document(
        id="chunk-1",
        page_content="x" * 1_500,
        metadata={
            "document_id": "42",
            "doc_hash": "version-1",
            "page": 0,
        },
    )

    first = build_citations([document])[0]
    second = build_citations([document])[0]

    assert first.id == second.id
    assert first.id.startswith("cit_")
    assert first.label == "S1"
    assert first.source.document_id == "42"
    assert first.source.document_version == "version-1"
    assert len(first.excerpt) == 1_000


def test_build_citations_keeps_offsets_and_page_totals_valid():
    citation = build_citations(
        [
            Document(
                page_content="Texto",
                metadata={
                    "start_index": 10,
                    "end_index": 2,
                    "total_pages": -1,
                },
            )
        ]
    )[0]

    assert citation.location.start_index == 10
    assert citation.location.end_index == 10
    assert citation.location.total_pages is None
