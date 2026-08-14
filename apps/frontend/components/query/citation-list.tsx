"use client";

import {
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import { CitationRow } from "@/components/query/citation-row";
import type { Citation } from "@/lib/validation/query";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <Sources className="mb-0 w-full text-foreground">
      <SourcesTrigger
        className="w-full justify-between border-b border-border pb-3 text-left"
        count={citations.length}
      >
        <span className="text-sm font-semibold">Fuentes utilizadas</span>
        <span className="text-xs font-normal text-muted-foreground">
          {citations.length} {citations.length === 1 ? "documento" : "documentos"}
        </span>
      </SourcesTrigger>
      <SourcesContent className="mt-0 w-full gap-0">
        {citations.map((citation) => (
          <CitationRow citation={citation} key={citation.id} />
        ))}
      </SourcesContent>
    </Sources>
  );
}
