"use client";

import { useRef, useState } from "react";

import { ChatComposer } from "@/components/workspace/chat-composer";
import { ChatMessageList } from "@/components/workspace/chat-message-list";
import { ChatWelcome } from "@/components/workspace/chat-welcome";
import { SourcesPanel } from "@/components/workspace/sources-panel";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import type { Citation } from "@/lib/validation/rag-stream";
import { cn } from "@/lib/utils";

export function ChatPage() {
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
    <div ref={pageRef} className="mx-auto flex min-h-0 w-full max-w-[80rem] flex-1 flex-col overflow-hidden px-4 md:px-8">
      <div
        className={cn(
          "grid min-h-0 flex-1 grid-cols-1 grid-rows-[minmax(0,1fr)] overflow-hidden transition-[grid-template-columns,gap] duration-300 ease-out",
          visiblePanelCitations.length
            ? activeCitation
              ? "lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-8"
              : "lg:grid-cols-[minmax(0,1fr)_0rem] lg:gap-0"
            : "lg:grid-cols-1",
        )}
      >
        <div className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <div
            className={cn(
              "min-h-0 flex-1",
              messages.length === 0 ? "overflow-y-auto pb-28" : "overflow-hidden",
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
        </div>
        <SourcesPanel
          activeCitation={activeCitation}
          citations={visiblePanelCitations}
          onClose={closeSources}
          onSelect={selectPanelCitation}
        />
      </div>
      <ChatComposer
        className={cn(
          "[left:var(--workspace-sidebar-offset)]",
          activeCitation ? "lg:right-[calc(20rem+2rem)]" : "lg:right-0",
        )}
      />
    </div>
  );
}
