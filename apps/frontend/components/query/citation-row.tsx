import { ExternalLink, FileText } from "lucide-react";

import { Separator } from "@/components/ui/separator";
import type { Citation } from "@/lib/validation/query";

export function CitationRow({ citation }: { citation: Citation }) {
  const page = citation.location.pageLabel || `página ${citation.location.page}`;

  return (
    <details className="group py-4 first:pt-4 last:pb-0">
      <summary className="flex cursor-pointer list-none items-start gap-3 text-left marker:hidden [&::-webkit-details-marker]:hidden">
        <FileText aria-hidden="true" className="mt-0.5 shrink-0 text-primary" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">
            {citation.source.filename}
          </span>
          <span className="mt-1 block text-xs text-muted-foreground">
            {citation.label} · {page}
            {citation.location.totalPages ? ` de ${citation.location.totalPages}` : ""}
          </span>
        </span>
        <span aria-hidden="true" className="text-xs text-muted-foreground transition-transform group-open:rotate-180">
          ↓
        </span>
      </summary>
      <div className="ml-8 mt-3 max-w-[65ch] border-l border-border pl-3 text-sm leading-6 text-muted-foreground">
        <p>{citation.excerpt}</p>
        {citation.source.url ? (
          <a
            className="mt-3 inline-flex min-h-11 items-center gap-1.5 font-medium text-primary underline-offset-4 hover:underline"
            href={citation.source.url}
            rel="noopener noreferrer"
            target="_blank"
          >
            Abrir fuente
            <ExternalLink aria-hidden="true" className="size-4" />
          </a>
        ) : null}
      </div>
      <Separator className="mt-4" />
    </details>
  );
}
