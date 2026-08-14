"use client";

import {
  ArrowLeftIcon,
  ArrowRightIcon,
  CheckIcon,
  CopyIcon,
  ExternalLinkIcon,
  XIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import { useIsMobile } from "@/hooks/use-mobile";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { Citation } from "@/lib/validation/rag-stream";

type SourcesPanelProps = {
  activeCitation: Citation | null;
  citations: Citation[];
  onClose: () => void;
  onSelect: (citation: Citation) => void;
};

function CitationSource({
  citation,
  index,
  onSelect,
  selected,
}: {
  citation: Citation;
  index: number;
  onSelect: () => void;
  selected: boolean;
}) {
  return (
    <button
      aria-current={selected ? "true" : undefined}
      className={cn(
        "flex w-full items-start gap-3 border-b border-sidebar-border/70 px-4 py-4 text-left transition-colors",
        "hover:bg-sidebar-accent/60 focus-visible:bg-sidebar-accent/60",
        selected && "bg-secondary-foreground/6",
      )}
      onClick={onSelect}
      type="button"
    >
      <span
        className={cn(
          "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
          selected
            ? "bg-secondary-foreground text-background"
            : "bg-secondary-foreground/15 text-secondary-foreground",
        )}
      >
        {index + 1}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-foreground">
          {citation.source.filename || `Fuente ${citation.label}`}
        </span>
        <span className="mt-1 block text-xs text-muted-foreground">
          Página {citation.location.pageLabel ?? citation.location.page}
        </span>
      </span>
    </button>
  );
}

function SourceDetails({ citation }: { citation: Citation }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const sourceUrl = citation.source.url;
  const citedPageUrl = sourceUrl
    ? `${sourceUrl}#page=${citation.location.page}`
    : null;

  async function copyUrl() {
    if (!sourceUrl) return;
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(sourceUrl);
      setCopyError(false);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopyError(true);
    }
  }

  return (
    <div className="flex flex-col gap-5 px-4 pb-5">
      <div className="border-l-2 border-secondary-foreground bg-secondary-foreground/7 px-4 py-3 text-sm leading-6 text-foreground/85">
        {citation.excerpt}
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        {citedPageUrl ? (
          <a
            className="inline-flex items-center gap-2 font-medium text-secondary-foreground underline-offset-4 hover:underline focus-visible:underline"
            href={citedPageUrl}
            rel="noopener noreferrer"
            target="_blank"
          >
            Abrir página citada
            <ExternalLinkIcon className="size-4" aria-hidden="true" />
          </a>
        ) : null}
        {sourceUrl ? (
          <button
            className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground"
            onClick={() => void copyUrl()}
            type="button"
          >
            {copied ? <CheckIcon className="size-4" /> : <CopyIcon className="size-4" />}
            {copied ? "Enlace copiado" : "Copiar enlace"}
          </button>
        ) : null}
      </div>
      {copyError ? (
        <p className="text-xs text-destructive" role="status">
          No se pudo copiar el enlace.
        </p>
      ) : null}
    </div>
  );
}

function SourceContent({
  activeCitation,
  citations,
  onClose,
  onSelect,
}: SourcesPanelProps) {
  const activeIndex = activeCitation
    ? citations.findIndex((citation) => citation.id === activeCitation.id)
    : -1;

  function selectByOffset(offset: number) {
    const citation = citations[activeIndex + offset];
    if (!citation) return;
    onSelect(citation);
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-1 flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-4 px-4 pb-4">
        <div>
          <h2 className="text-base font-semibold tracking-[-0.02em]">Fuentes consultadas</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {citations.length} {citations.length === 1 ? "fuente" : "fuentes"}
          </p>
        </div>
        <button
          aria-label="Cerrar fuentes"
          className="flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          onClick={onClose}
          type="button"
        >
          <XIcon className="size-4" aria-hidden="true" />
        </button>
      </div>
      <div className="min-h-0 w-full flex-1 overflow-y-auto border-t border-sidebar-border/70">
        {citations.map((citation, index) => (
          <div key={citation.id} data-source-id={citation.id}>
            <CitationSource
              citation={citation}
              index={index}
              onSelect={() => onSelect(citation)}
              selected={citation.id === activeCitation?.id}
            />
            {citation.id === activeCitation?.id ? <SourceDetails citation={citation} /> : null}
          </div>
        ))}
      </div>
      {activeCitation && citations.length > 1 ? (
        <div className="flex items-center justify-between border-t border-sidebar-border/70 px-4 py-3 text-xs text-muted-foreground">
          <button
            className="inline-flex items-center gap-1 hover:text-foreground disabled:opacity-40"
            disabled={activeIndex <= 0}
            onClick={() => selectByOffset(-1)}
            type="button"
          >
            <ArrowLeftIcon className="size-3.5" /> Anterior
          </button>
          <span>
            {activeIndex + 1} / {citations.length}
          </span>
          <button
            className="inline-flex items-center gap-1 hover:text-foreground disabled:opacity-40"
            disabled={activeIndex === citations.length - 1}
            onClick={() => selectByOffset(1)}
            type="button"
          >
            Siguiente <ArrowRightIcon className="size-3.5" />
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function SourcesPanel({
  activeCitation,
  citations,
  onClose,
  onSelect,
}: SourcesPanelProps) {
  const open = activeCitation !== null;
  const isMobile = useIsMobile();

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);

  if (!citations.length) return null;

  return (
    <>
      <aside
        id="sources-panel"
        aria-label="Fuentes consultadas"
        className={cn(
          "hidden h-full min-h-0 w-full min-w-0 self-stretch overflow-hidden border-l border-sidebar-border/70 py-6 transition-[opacity,transform] duration-300 ease-out lg:flex",
          open
            ? "lg:translate-x-0 lg:opacity-100"
            : "pointer-events-none lg:translate-x-3 lg:opacity-0",
        )}
      >
        <SourceContent
          activeCitation={activeCitation}
          citations={citations}
          onClose={onClose}
          onSelect={onSelect}
        />
      </aside>
      {open && isMobile ? (
        <Sheet open onOpenChange={(nextOpen) => !nextOpen && onClose()}>
          <SheetContent
            aria-describedby="mobile-sources-description"
            className="max-h-[78dvh] gap-0 border-sidebar-border bg-popover p-0 lg:hidden"
            side="bottom"
            showCloseButton={false}
          >
            <SheetHeader className="sr-only">
              <SheetTitle>Fuentes consultadas</SheetTitle>
              <SheetDescription id="mobile-sources-description">
                Fuentes asociadas a la respuesta seleccionada
              </SheetDescription>
            </SheetHeader>
            <SourceContent
              activeCitation={activeCitation}
              citations={citations}
              onClose={onClose}
              onSelect={onSelect}
            />
          </SheetContent>
        </Sheet>
      ) : null}
    </>
  );
}
