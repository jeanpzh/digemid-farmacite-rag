"use client";

import {
  ArrowRightIcon,
  ExternalLinkIcon,
  XIcon,
} from "lucide-react";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { useIsMobile } from "@/hooks/use-mobile";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { Citation } from "@/lib/validation/rag-stream";
import { getCitationDocumentType } from "@/lib/workspace-view-model";

const PdfPreview = dynamic(
  () =>
    import("@/components/query/pdf-preview").then(
      (module) => module.PdfPreview,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex aspect-[0.78] w-full items-center justify-center rounded-xl border border-border bg-muted/40 text-xs text-muted-foreground">
        Cargando PDF...
      </div>
    ),
  },
);

type SourcesPanelProps = {
  activeCitation: Citation | null;
  citations: Citation[];
  onClose: () => void;
  onSelect: (citation: Citation) => void;
};

function CitationSource({
  citation,
  onSelect,
  selected,
}: {
  citation: Citation;
  onSelect: () => void;
  selected: boolean;
}) {
  return (
    <button
      aria-current={selected ? "true" : undefined}
      className={cn(
        "group flex w-full flex-col gap-3 rounded-xl border p-3 text-left transition-[border-color,background-color,transform] duration-200",
        "border-sidebar-border/70 bg-background/35 hover:-translate-y-0.5 hover:border-brand-accent hover:bg-secondary hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent",
        selected && "border-secondary-foreground/80 bg-secondary-foreground/8",
      )}
      onClick={onSelect}
      type="button"
    >
      <span className="flex items-center justify-between gap-2">
        <span
          className={cn(
            "flex size-7 items-center justify-center rounded-lg text-[11px] font-semibold",
            selected
              ? "bg-secondary-foreground text-background"
              : "bg-secondary-foreground/12 text-secondary-foreground",
          )}
        >
          {citation.label.replace(/^S/, "")}
        </span>
        <ArrowRightIcon
          className="size-3.5 text-muted-foreground transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-secondary-foreground"
          aria-hidden="true"
        />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-xs font-semibold text-foreground">
          {citation.source.filename || `Fuente ${citation.label}`}
        </span>
        <span className="mt-1 block text-[11px] text-muted-foreground">
          Página {citation.location.pageLabel ?? citation.location.page}
        </span>
      </span>
    </button>
  );
}

function CitationIndexRail({
  activeCitation,
  citations,
  onSelect,
}: {
  activeCitation: Citation;
  citations: Citation[];
  onSelect: (citation: Citation) => void;
}) {
  return (
    <nav
      aria-label="Índice de evidencia"
      className="relative hidden min-h-0 flex-col items-center overflow-y-auto border-r border-border bg-card/55 px-2 py-5 lg:flex"
    >
      <div className="absolute top-8 bottom-8 left-1/2 w-px -translate-x-1/2 bg-brand-accent/35" aria-hidden="true" />
      <div className="relative flex flex-col gap-2.5">
        {citations.map((citation) => {
          const selected = citation.id === activeCitation.id;
          return (
            <button
              aria-current={selected ? "true" : undefined}
              aria-label={`Abrir evidencia ${citation.label}`}
              className={cn(
                "flex size-8 items-center justify-center rounded-full border bg-card text-[11px] font-semibold tabular-nums text-muted-foreground transition-[background-color,border-color,color,transform] hover:scale-105 hover:border-brand-accent hover:bg-secondary hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent",
                selected && "border-brand-accent bg-brand-accent text-brand-accent-foreground shadow-sm",
              )}
              key={citation.id}
              onClick={() => onSelect(citation)}
              type="button"
            >
              {citation.label.replace(/^S/, "")}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

function CitationCarousel({
  activeCitation,
  citations,
  onSelect,
}: {
  activeCitation: Citation;
  citations: Citation[];
  onSelect: (citation: Citation) => void;
}) {
  const [api, setApi] = useState<CarouselApi>();
  const activeIndex = citations.findIndex(
    (citation) => citation.id === activeCitation.id,
  );

  useEffect(() => {
    if (!api || activeIndex < 0) return;
    if (api.selectedScrollSnap() !== activeIndex) api.scrollTo(activeIndex);
  }, [activeIndex, api]);

  return (
    <Carousel
      className="w-full px-5"
      opts={{ align: "start", containScroll: "trimSnaps" }}
      setApi={(nextApi) => setApi(() => nextApi)}
    >
      <CarouselContent className="-ml-2">
        {citations.map((citation) => (
          <CarouselItem
            className="basis-[82%] pl-2 sm:basis-[68%]"
            key={citation.id}
          >
            <CitationSource
              citation={citation}
              onSelect={() => onSelect(citation)}
              selected={citation.id === activeCitation.id}
            />
          </CarouselItem>
        ))}
      </CarouselContent>
      {citations.length > 1 ? (
        <>
          <CarouselPrevious
            aria-label="Evidencia anterior"
            className="-left-1 size-7"
          />
          <CarouselNext
            aria-label="Evidencia siguiente"
            className="-right-1 size-7"
          />
        </>
      ) : null}
    </Carousel>
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

  return (
    <div className="flex h-full min-h-0 w-full flex-1 flex-col overflow-hidden">
      <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border bg-card/50 px-5 py-5">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-brand-accent">
            Evidencia {String(activeIndex + 1).padStart(2, "0")} de {String(citations.length).padStart(2, "0")}
          </p>
          <h2 className="mt-2 truncate font-editorial text-xl font-semibold tracking-[-0.025em] text-foreground">
            {activeCitation?.source.filename ?? "Revisión de fuentes"}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {activeCitation
              ? `${getCitationDocumentType(activeCitation.source.filename)} · Página ${activeCitation.location.pageLabel ?? activeCitation.location.page}${activeCitation.location.totalPages ? ` de ${activeCitation.location.totalPages}` : ""}`
              : "Compruebe el pasaje exacto detrás de la respuesta."}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {activeCitation?.source.url ? (
            <a
              aria-label="Abrir documento original"
              className="flex size-9 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent"
              href={`${activeCitation.source.url}#page=${activeCitation.location.page}`}
              rel="noopener noreferrer"
              target="_blank"
            >
              <ExternalLinkIcon className="size-4" aria-hidden="true" />
            </a>
          ) : null}
          <button
            aria-label="Cerrar fuentes"
            className="flex size-9 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent lg:hidden"
            onClick={onClose}
            type="button"
          >
            <XIcon className="size-4" aria-hidden="true" />
          </button>
        </div>
      </header>
      <div className="min-h-0 w-full flex-1 overflow-y-auto">
        {activeCitation ? (
          <div className="space-y-5 px-4 py-4">
            <div className="rounded-2xl border border-border bg-card/65 p-2.5 shadow-[0_18px_50px_-38px_rgba(19,36,51,0.35)]">
              <PdfPreview
                citation={activeCitation}
                key={activeCitation.id}
              />
            </div>

            <section aria-label="Fuentes de esta respuesta" className="lg:hidden">
              <div className="mb-3 flex items-end justify-between gap-3 px-1">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Navegar evidencia
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Seleccione otra cita para comparar.
                  </p>
                </div>
                <span className="text-[11px] tabular-nums text-muted-foreground">
                  {activeIndex + 1} / {citations.length}
                </span>
              </div>
              <CitationCarousel
                activeCitation={activeCitation}
                citations={citations}
                onSelect={onSelect}
              />
            </section>
          </div>
        ) : null}
      </div>
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
          "hidden h-full min-h-0 w-full min-w-0 self-stretch overflow-hidden border-l border-border bg-[#f7f3ea] transition-[opacity,transform] duration-300 ease-out lg:grid lg:grid-cols-[3.25rem_minmax(0,1fr)]",
          open
            ? "lg:translate-x-0 lg:opacity-100"
            : "pointer-events-none lg:translate-x-3 lg:opacity-0",
        )}
      >
        {activeCitation ? (
          <CitationIndexRail
            activeCitation={activeCitation}
            citations={citations}
            onSelect={onSelect}
          />
        ) : null}
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
