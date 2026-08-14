from langchain_core.documents import Document

class ContextBuilder:
    def build(self, documents: list[Document]) -> str:
        sources = []
        for index, document in enumerate(documents, start=1):
            metadata = document.metadata
            source_id = f"S{index}"
            chunk_id = document.id or metadata.get("chunk_id") or "unknown"
            metadata_lines = [
                f"chunk_id: {chunk_id}",
                f"document_id: {metadata.get('document_id', 'unknown')}",
                f"document_version: {metadata.get('document_version', metadata.get('doc_hash', 'unknown'))}",
                f"filename: {metadata.get('filename', 'unknown')}",
                f"source_url: {metadata.get('source_url', 'unknown')}",
                f"page: {metadata.get('page', 'unknown')}",
                f"page_label: {metadata.get('page_label', 'unknown')}",
                f"start_index: {metadata.get('start_index', 'unknown')}",
                f"end_index: {metadata.get('end_index', 'unknown')}",
            ]
            metadata_text = "\n".join(metadata_lines)
            sources.append(
                f"[{source_id}]\n"
                f"{metadata_text}\n"
                f"content: {document.page_content}"
            )

        return "\n\n".join(sources)
