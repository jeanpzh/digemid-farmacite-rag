"use client";

import { cn } from "@/lib/utils";
import type { Citation } from "@/lib/validation/rag-stream";

export function CitationPart({
  active,
  citation,
  onClick,
}: {
  active: boolean;
  citation: Citation;
  onClick: () => void;
}) {
  const label = citation.label.replace(/^S/, "");

  return (
    <button
      aria-controls="sources-panel"
      aria-expanded={active}
      aria-label={`Abrir fuente ${citation.label}`}
      className={cn(
        "mx-1 inline-flex min-h-6 min-w-6 translate-y-[-1px] items-center justify-center rounded border px-1.5 align-baseline text-xs font-semibold leading-none transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary-foreground",
        active
          ? "border-secondary-foreground bg-secondary-foreground text-background"
          : "border-secondary-foreground/60 bg-secondary-foreground/8 text-secondary-foreground hover:bg-secondary-foreground/18",
      )}
      data-citation-id={citation.id}
      onClick={onClick}
      type="button"
    >
      [{label}]
    </button>
  );
}
