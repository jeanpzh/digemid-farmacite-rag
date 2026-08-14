"use client";

import { Document, Page, pdfjs } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { useState } from "react";

import type { Citation } from "@/lib/validation/query";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

const documentCache = new Map<string, PDFDocumentProxy>();

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightTextLayer(text: string, snippet: string) {
  const terms = snippet
    .split(/\s+/)
    .map((term) => term.replace(/[^\p{L}\p{N}-]/gu, ""))
    .filter((term) => term.length > 3)
    .slice(0, 12);

  let html = escapeHtml(text);
  for (const term of terms) {
    html = html.replace(
      new RegExp(`(${escapeRegExp(escapeHtml(term))})`, "giu"),
      '<mark class="bg-orange-300/70 text-inherit">$1</mark>'
    );
  }
  return html;
}

function PreviewFallback({ citation }: { citation: Citation }) {
  return (
    <div className="flex min-h-56 flex-col justify-center gap-3 rounded-lg border border-dashed border-border bg-muted/30 p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        Vista previa no disponible
      </p>
      <p className="text-sm leading-6 text-foreground/80">
        Esta fuente no incluye un PDF accesible, pero este es el pasaje
        recuperado:
      </p>
      <blockquote className="border-l-2 border-orange-500/70 pl-3 text-sm leading-6 text-muted-foreground">
        {citation.excerpt}
      </blockquote>
    </div>
  );
}

export function PdfPreview({ citation }: { citation: Citation }) {
  const sourceUrl = citation.source.url;
  const [failedSourceUrl, setFailedSourceUrl] = useState<string | null>(null);
  const cachedDocument = sourceUrl ? documentCache.get(sourceUrl) : undefined;
  const error = sourceUrl === failedSourceUrl;

  if (!sourceUrl || error) {
    return <PreviewFallback citation={citation} />;
  }

  const page = Math.max(1, citation.location.page);
  const renderPage = (pdf?: PDFDocumentProxy) => (
    <div className="flex min-h-0 justify-center overflow-auto rounded-lg bg-white p-2 shadow-sm">
      <Page
        customTextRenderer={({ str }) =>
          highlightTextLayer(str, citation.excerpt)
        }
        pdf={pdf}
        pageNumber={page}
        renderAnnotationLayer
        renderTextLayer
        width={260}
      />
    </div>
  );

  if (cachedDocument) {
    return renderPage(cachedDocument);
  }

  return (
    <Document
      error={<PreviewFallback citation={citation} />}
      file={sourceUrl}
      loading={
        <div className="flex min-h-56 items-center justify-center rounded-lg bg-muted/30 text-sm text-muted-foreground">
          Cargando página {page}...
        </div>
      }
      onLoadError={() => setFailedSourceUrl(sourceUrl)}
      onLoadSuccess={(document) => {
        documentCache.set(sourceUrl, document);
      }}
    >
      {renderPage()}
    </Document>
  );
}
