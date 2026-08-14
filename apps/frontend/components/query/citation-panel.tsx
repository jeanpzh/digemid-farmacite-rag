"use client";

import { Button } from "@/components/ui/button";
import type { Citation } from "@/lib/validation/query";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowUpRightIcon, XIcon } from "lucide-react";

import { PdfPreview } from "@/components/query/pdf-preview";

type CitationPanelProps = {
  open: boolean;
  active?: Citation;
  others: Citation[];
  onSelect: (id: string) => void;
  onClose: () => void;
};

function PanelContents({
  active,
  others,
  onSelect,
  onClose,
}: Omit<CitationPanelProps, "open"> & { active: Citation }) {
  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-background">
      <header className="flex shrink-0 items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-orange-500">
            Fuente {active.label}
          </p>
          <h2 className="mt-1 truncate text-sm font-semibold">
            {active.source.filename}
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Página {active.location.pageLabel ?? active.location.page}
            {active.location.totalPages ? ` de ${active.location.totalPages}` : ""}
          </p>
        </div>
        <Button
          aria-label="Cerrar fuentes"
          className="-mr-1 shrink-0"
          onClick={onClose}
          size="icon-sm"
          type="button"
          variant="ghost"
        >
          <XIcon />
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <PdfPreview citation={active} />

        {others.length > 0 ? (
          <section className="mt-5 border-t border-border pt-4">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Otras fuentes de esta respuesta
            </p>
            <div className="space-y-1" role="list">
              {others.map((citation) => (
                <button
                  className="flex w-full items-center gap-3 rounded-md p-2 text-left transition-colors hover:bg-muted"
                  key={citation.id}
                  onClick={() => onSelect(citation.id)}
                  type="button"
                >
                  <span className="flex size-6 shrink-0 items-center justify-center rounded bg-orange-500/10 text-xs font-semibold text-orange-600">
                    {citation.label}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-medium">
                      {citation.source.filename}
                    </span>
                    <span className="mt-0.5 block text-[11px] text-muted-foreground">
                      Página {citation.location.pageLabel ?? citation.location.page}
                    </span>
                  </span>
                  <ArrowUpRightIcon className="size-3.5 shrink-0 text-muted-foreground" />
                </button>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}

export function CitationPanel({
  open,
  active,
  others,
  onSelect,
  onClose,
}: CitationPanelProps) {
  const shouldReduceMotion = useReducedMotion();
  const duration = shouldReduceMotion ? 0 : 0.3;

  return (
    <AnimatePresence initial={false}>
      {open && active ? (
        <>
          <motion.button
            aria-label="Cerrar panel de fuentes"
            className="fixed inset-0 z-30 bg-black/20 md:hidden"
            initial={shouldReduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            transition={{ duration }}
            type="button"
          />
          <motion.aside
            aria-label="Fuente citada"
            className="fixed inset-x-0 bottom-0 z-40 h-[min(72dvh,560px)] overflow-hidden rounded-t-2xl border-t border-border shadow-2xl md:hidden"
            initial={shouldReduceMotion ? false : { opacity: 0, y: "100%" }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: "100%" }}
            transition={{ duration, ease: [0.4, 0, 0.2, 1] }}
          >
            <PanelContents
              active={active}
              onClose={onClose}
              onSelect={onSelect}
              others={others}
            />
          </motion.aside>
          <motion.aside
            aria-label="Fuente citada"
            className="hidden h-full w-[300px] shrink-0 overflow-hidden border-l border-border md:block"
            initial={shouldReduceMotion ? false : { opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: 300 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, width: 0 }}
            transition={{ duration, ease: [0.4, 0, 0.2, 1] }}
          >
            <PanelContents
              active={active}
              onClose={onClose}
              onSelect={onSelect}
              others={others}
            />
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );
}
