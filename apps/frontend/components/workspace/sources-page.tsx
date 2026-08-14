"use client";

import { useWorkspace } from "@/components/workspace/workspace-provider";
import { WorkspaceSection } from "@/components/workspace/workspace-section";

export function SourcesPage() {
  const { citations } = useWorkspace();

  return (
    <WorkspaceSection className="py-16 md:py-24">
      <div className="reveal-on-load">
        <h1 className="max-w-4xl text-4xl font-semibold tracking-[-0.055em] md:text-6xl">
          Fuentes consultadas
        </h1>
        <p className="mt-5 max-w-xl text-sm leading-6 text-muted-foreground">
          Las fuentes aparecen aquí cuando el asistente las recupera.
        </p>
      </div>
      {citations.length === 0 ? (
        <div className="reveal-on-load mt-20 rounded-[1.5rem] bg-card p-8 ring-1 ring-foreground/8 md:p-12">
          <p className="max-w-md text-xl font-medium tracking-[-0.02em]">
            Todavía no hay fuentes en esta sesión.
          </p>
          <p className="mt-3 max-w-md text-sm leading-6 text-muted-foreground">
            Vuelva a la conversación y formule una pregunta para iniciar la
            recuperación documental.
          </p>
        </div>
      ) : (
        <div className="mt-20 grid grid-cols-1 gap-6 md:grid-cols-2">
          {citations.map((citation) => (
            <article
              key={citation.id}
              className="rounded-[1.5rem] bg-card p-6 ring-1 ring-foreground/8"
            >
              <span className="flex size-8 items-center justify-center rounded-lg bg-foreground text-xs font-semibold text-background">
                {citation.label.replace(/^S/, "")}
              </span>
              <h2 className="mt-8 truncate text-lg font-medium tracking-[-0.025em]">
                {citation.source.filename}
              </h2>
              <p className="mt-2 text-xs text-muted-foreground">
                Página {citation.location.pageLabel ?? citation.location.page}
              </p>
              <p className="mt-6 text-sm leading-6 text-muted-foreground">
                {citation.excerpt}
              </p>
            </article>
          ))}
        </div>
      )}
    </WorkspaceSection>
  );
}
