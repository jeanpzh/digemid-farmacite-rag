export function getDocumentPdfUrl(
  documentId: string,
  documentVersion: string,
): string | null {
  if (documentId === "unknown" || documentVersion === "unknown") return null;

  return `/api/v1/documents/${encodeURIComponent(documentId)}/pdf?version=${encodeURIComponent(documentVersion)}`;
}
