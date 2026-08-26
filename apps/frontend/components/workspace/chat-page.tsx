"use client";

import { PanelRightCloseIcon } from "lucide-react";
import { useRef, useState } from "react";

import { ChatComposer } from "@/components/workspace/chat-composer";
import { ChatMessageList } from "@/components/workspace/chat-message-list";
import { ChatWelcome } from "@/components/workspace/chat-welcome";
import { SourcesPanel } from "@/components/workspace/sources-panel";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import type { Citation } from "@/lib/validation/rag-stream";
import { cn } from "@/lib/utils";
import { getConsultationTitle } from "@/lib/workspace-view-model";

export function ChatPage() {
  const { conversationId } = useWorkspace();

  return <ConversationPage key={conversationId} />;
}

function ConversationPage() {
  const pageRef = useRef<HTMLDivElement>(null);
  const {
    error,
    isLoading,
    messages,
    retrievalStatus,
    submitQuestion,
  } = useWorkspace();
  const [selectedCitation, setSelectedCitation] = useState<{
    citationId: string;
    messageId: string;
  } | null>(null);
  const [panelCitations, setPanelCitations] = useState<Citation[]>([]);
  const citationTriggerRef = useRef<string | null>(null);

  const visiblePanelCitations = messages.length === 0 ? [] : panelCitations;
  const activeCitation = selectedCitation
    ? visiblePanelCitations.find(
        (citation) => citation.id === selectedCitation.citationId,
      ) ?? null
    : null;
  const lastUserQuestion = [...messages]
    .reverse()
    .find((message) => message.role === "user")
    ?.parts.filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("")
    .trim();
  const consultationTitle = getConsultationTitle(lastUserQuestion);

  function selectCitation(
    citation: Citation,
    citations: Citation[],
    messageId: string,
  ) {
    citationTriggerRef.current = citation.id;
    setPanelCitations(citations);
    setSelectedCitation({
      citationId: citation.id,
      messageId,
    });
  }

  function selectPanelCitation(citation: Citation) {
    citationTriggerRef.current = citation.id;
    if (!selectedCitation) return;
    setSelectedCitation({ ...selectedCitation, citationId: citation.id });
  }

  function closeSources() {
    setSelectedCitation(null);
    setPanelCitations([]);
    window.requestAnimationFrame(() => {
      document
        .querySelector<HTMLButtonElement>(
          `[data-citation-id="${CSS.escape(citationTriggerRef.current ?? "")}"]`,
        )
        ?.focus();
    });
  }

  return (
    <div ref={pageRef} className="flex min-h-0 w-full flex-1 flex-col overflow-hidden bg-background">
      <header className="flex h-15 shrink-0 items-center justify-between gap-4 border-b border-border bg-card/65 px-5 md:px-7">
        <div className="flex min-w-0 items-center gap-3 text-sm">
          <span className="shrink-0 font-medium text-muted-foreground">Consultas</span>
          <span aria-hidden="true" className="text-border">/</span>
          <span className="truncate font-semibold tracking-[-0.02em] text-foreground">
            {consultationTitle}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {activeCitation ? (
            <button
              className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent"
              onClick={closeSources}
              type="button"
            >
              <PanelRightCloseIcon className="size-4" aria-hidden="true" />
              <span className="hidden sm:inline">Colapsar evidencia</span>
            </button>
          ) : null}
        </div>
      </header>
      <div
        className={cn(
          "grid min-h-0 flex-1 grid-cols-1 grid-rows-[minmax(0,1fr)] overflow-hidden transition-[grid-template-columns,gap] duration-300 ease-out",
          visiblePanelCitations.length
            ? activeCitation
              ? "lg:grid-cols-[minmax(26rem,0.92fr)_minmax(32rem,1.08fr)]"
              : "lg:grid-cols-[minmax(0,1fr)_0rem] lg:gap-0"
            : "lg:grid-cols-1",
        )}
      >
        <section aria-label="Consulta" className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <div
            className={cn(
              "min-h-0 flex-1",
              messages.length === 0 ? "overflow-y-auto px-6" : "overflow-hidden",
            )}
          >
            {messages.length === 0 ? (
              <ChatWelcome onSuggestedQuestion={submitQuestion} />
            ) : (
              <ChatMessageList
                activeCitationId={selectedCitation?.citationId ?? null}
                activeMessageId={selectedCitation?.messageId ?? null}
                error={error ? "No pudimos completar la consulta. Inténtelo nuevamente." : undefined}
                messages={messages}
                onCitationClick={selectCitation}
                onRetry={lastUserQuestion ? () => submitQuestion(lastUserQuestion) : undefined}
                retrievalStatus={retrievalStatus}
              />
            )}
            {isLoading ? (
              <div className="pointer-events-none h-0 overflow-visible text-center text-[11px] text-muted-foreground">
                <span className="inline-flex items-center gap-2 rounded-full bg-background px-3 py-1 ring-1 ring-foreground/8">
                  <span className="size-1.5 animate-pulse rounded-full bg-secondary-foreground" />
                  Preparando respuesta
                </span>
              </div>
            ) : null}
          </div>
          <ChatComposer />
        </section>
        <SourcesPanel
          activeCitation={activeCitation}
          citations={visiblePanelCitations}
          onClose={closeSources}
          onSelect={selectPanelCitation}
        />
      </div>
    </div>
  );
}
