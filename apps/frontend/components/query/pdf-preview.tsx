"use client";

import {
  ChevronLeftIcon,
  ChevronRightIcon,
  RotateCcwIcon,
  ZoomInIcon,
  ZoomOutIcon,
} from "lucide-react";
import { Document, Page, pdfjs } from "react-pdf";
import { useState, type ReactNode } from "react";

import { getDocumentPdfUrl } from "@/lib/document-url";
import {
  changePdfScale,
  getAdjacentPdfPage,
  MAX_PDF_SCALE,
  MIN_PDF_SCALE,
} from "@/lib/pdf-controls";
import type { Citation } from "@/lib/validation/query";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

const PAGE_WIDTH = 480;
const PDF_FRAME_CLASS =
  "relative flex aspect-[0.78] w-full max-h-[64dvh] min-h-0 items-start justify-center overflow-auto rounded-xl border border-border bg-[#e9e4da] p-3 shadow-inner";

function PdfPageFrame({ children }: { children: ReactNode }) {
  return <div className={PDF_FRAME_CLASS}>{children}</div>;
}

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
      '<mark class="bg-secondary-foreground/35 text-inherit">$1</mark>'
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
        No se pudo cargar el PDF almacenado, pero este es el pasaje recuperado:
      </p>
      <blockquote className="border-l-2 border-secondary-foreground/70 pl-3 text-sm leading-6 text-muted-foreground">
        {citation.excerpt}
      </blockquote>
    </div>
  );
}

function PdfDocumentViewer({
  citation,
  pdfUrl,
}: {
  citation: Citation;
  pdfUrl: string;
}) {
  const initialPage = Math.max(1, citation.location.page);
  const [page, setPage] = useState(initialPage);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [scale, setScale] = useState(1);
  const [hasError, setHasError] = useState(false);

  function renderPage() {
    return (
      <PdfPageFrame>
        <Page
          customTextRenderer={({ str }) =>
            highlightTextLayer(str, citation.excerpt)
          }
          pageNumber={page}
          renderAnnotationLayer
          renderTextLayer
          width={Math.round(PAGE_WIDTH * scale)}
        />
      </PdfPageFrame>
    );
  }

  if (hasError) {
    return <PreviewFallback citation={citation} />;
  }

  const totalPages = numPages;
  const canGoNext = totalPages !== null && page < totalPages;
  const controlClassName =
    "inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-background hover:text-foreground disabled:pointer-events-none disabled:opacity-35 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary-foreground";
  const pdf = (
    <Document
      error={<PreviewFallback citation={citation} />}
      file={pdfUrl}
      loading={
        <PdfPageFrame>
          <div className="absolute inset-2 flex items-center justify-center rounded-md bg-muted/30 text-sm text-muted-foreground">
            Cargando página {initialPage}...
          </div>
        </PdfPageFrame>
      }
      onLoadError={() => setHasError(true)}
      onLoadSuccess={(document) => {
        setNumPages(document.numPages);
        setPage((currentPage) =>
          getAdjacentPdfPage(currentPage, 0, document.numPages),
        );
      }}
    >
      {renderPage()}
    </Document>
  );

  return (
    <div className="space-y-2">
      <div className="rounded-xl border border-border bg-card px-2.5 py-2 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-0.5">
            <button
              aria-label="Página anterior"
              className={controlClassName}
              disabled={page <= 1}
              onClick={() =>
                setPage((currentPage) =>
                  getAdjacentPdfPage(currentPage, -1, totalPages ?? 1),
                )
              }
              type="button"
            >
              <ChevronLeftIcon className="size-4" aria-hidden="true" />
            </button>
            <span className="min-w-24 text-center text-[11px] font-medium tabular-nums text-foreground">
              Página {page} de {totalPages ?? "—"}
            </span>
            <button
              aria-label="Página siguiente"
              className={controlClassName}
              disabled={!canGoNext}
              onClick={() =>
                setPage((currentPage) =>
                  getAdjacentPdfPage(currentPage, 1, totalPages ?? 1),
                )
              }
              type="button"
            >
              <ChevronRightIcon className="size-4" aria-hidden="true" />
            </button>
          </div>
          <div className="flex items-center gap-0.5 border-l border-border pl-2">
            <button
              aria-label="Reducir zoom"
              className={controlClassName}
              disabled={scale <= MIN_PDF_SCALE}
              onClick={() => setScale((current) => changePdfScale(current, -0.25))}
              type="button"
            >
              <ZoomOutIcon className="size-3.5" aria-hidden="true" />
            </button>
            <button
              aria-label="Restablecer zoom"
              className="min-h-8 min-w-12 rounded-md px-1 text-[10px] tabular-nums text-muted-foreground hover:bg-muted hover:text-foreground"
              onClick={() => setScale(1)}
              type="button"
            >
              {Math.round(scale * 100)}%
            </button>
            <button
              aria-label="Aumentar zoom"
              className={controlClassName}
              disabled={scale >= MAX_PDF_SCALE}
              onClick={() => setScale((current) => changePdfScale(current, 0.25))}
              type="button"
            >
              <ZoomInIcon className="size-3.5" aria-hidden="true" />
            </button>
            <button
              aria-label="Restablecer vista"
              className={controlClassName}
              onClick={() => {
                setPage(initialPage);
                setScale(1);
              }}
              type="button"
            >
              <RotateCcwIcon className="size-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
      {pdf}
    </div>
  );
}

export function PdfPreview({ citation }: { citation: Citation }) {
  const pdfUrl = getDocumentPdfUrl(
    citation.source.documentId,
    citation.source.documentVersion,
  );

  if (!pdfUrl) {
    return <PreviewFallback citation={citation} />;
  }

  return (
    <PdfDocumentViewer
      citation={citation}
      key={`${pdfUrl}:${citation.location.page}`}
      pdfUrl={pdfUrl}
    />
  );
}
