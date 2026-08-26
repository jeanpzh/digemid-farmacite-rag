"use client";

import {
  ArrowRightIcon,
  CheckCircleIcon,
  FileTextIcon,
} from "@phosphor-icons/react";

import type { ChatMessage } from "@/components/workspace/workspace-provider";
import {
  getAssistantCitations,
  getAssistantText,
  MarkdownCitationResponse,
} from "@/components/workspace/markdown-citation-response";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import { Reasoning, ReasoningTrigger } from "@/components/ai-elements/reasoning";
import { cn } from "@/lib/utils";
import type { RetrievalStatus } from "@/lib/validation/rag-stream";
import type { Citation } from "@/lib/validation/rag-stream";
import { getCitationDocumentType } from "@/lib/workspace-view-model";

export function ChatMessageList({
  activeCitationId,
  activeMessageId,
  error,
  messages,
  onCitationClick,
  onRetry,
  retrievalStatus,
}: {
  activeCitationId: string | null;
  activeMessageId: string | null;
  error?: string;
  messages: ChatMessage[];
  onCitationClick: (
    citation: Citation,
    citations: Citation[],
    messageId: string,
  ) => void;
  onRetry?: () => void;
  retrievalStatus: RetrievalStatus | null;
}) {
  return (
    <Conversation aria-label="Conversación" className="h-full min-h-0 flex-1">
      <ConversationContent className="mx-auto w-full max-w-none gap-7 px-5 pt-7 pb-8 md:px-8 md:pt-8">
        {messages.map((message, messageIndex) => (
          <Message
            key={message.id}
            from={message.role}
            className={cn(
              "reveal-on-load",
              message.role === "user"
                ? "ml-0 max-w-full"
                : "max-w-full",
            )}
          >
            {message.role === "user" ? (
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Pregunta
              </p>
            ) : null}
            <MessageContent
              className={cn(
                "text-[0.95rem] leading-7",
                message.role === "user"
                  ? "group-[.is-user]:w-full group-[.is-user]:rounded-xl group-[.is-user]:border group-[.is-user]:border-border group-[.is-user]:bg-card group-[.is-user]:px-5 group-[.is-user]:py-4 group-[.is-user]:font-editorial group-[.is-user]:text-lg group-[.is-user]:leading-7 group-[.is-user]:shadow-sm"
                  : "group-[.is-assistant]:w-full",
              )}
            >
              {message.role === "assistant" &&
              messageIndex === messages.length - 1 &&
              retrievalStatus ? (
                <Reasoning
                  defaultOpen={retrievalStatus.state === "active"}
                  isStreaming={retrievalStatus.state === "active"}
                >
                  <ReasoningTrigger
                    getThinkingMessage={() => retrievalStatus.label}
                  />
                </Reasoning>
              ) : null}
              {message.role === "assistant" ? (
                <AssistantParts
                  activeCitationId={activeCitationId}
                  active={activeMessageId === message.id}
                  message={message}
                  isRetrieving={retrievalStatus?.state === "active"}
                  onCitationClick={onCitationClick}
                />
              ) : (
                message.parts.map((part, index) =>
                  part.type === "text" ? (
                    <MessageResponse key={`${message.id}-${index}`}>
                      {part.text}
                    </MessageResponse>
                  ) : null,
                )
              )}
            </MessageContent>
          </Message>
        ))}
        {error ? (
          <div className="flex items-center justify-between gap-4 rounded-2xl bg-destructive/8 px-4 py-3 text-sm text-destructive ring-1 ring-destructive/15" role="alert">
            <span>{error}</span>
            {onRetry ? (
              <button
                className="shrink-0 rounded-md px-2 py-1 font-medium underline underline-offset-4 hover:bg-destructive/10"
                onClick={onRetry}
                type="button"
              >
                Reintentar
              </button>
            ) : null}
          </div>
        ) : null}
        {retrievalStatus && messages.at(-1)?.role !== "assistant" ? (
          <Message from="assistant" key="retrieval-status">
            <MessageContent>
              <Reasoning
                defaultOpen={retrievalStatus.state === "active"}
                isStreaming={retrievalStatus.state === "active"}
              >
                <ReasoningTrigger
                  getThinkingMessage={() => retrievalStatus.label}
                />
              </Reasoning>
            </MessageContent>
          </Message>
        ) : null}
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>
  );
}

function AssistantParts({
  active,
  activeCitationId,
  message,
  isRetrieving,
  onCitationClick,
}: {
  active: boolean;
  activeCitationId: string | null;
  isRetrieving: boolean;
  message: ChatMessage;
  onCitationClick: (
    citation: Citation,
    citations: Citation[],
    messageId: string,
  ) => void;
}) {
  const citations = getAssistantCitations(message.parts);
  const text = getAssistantText(message.parts);
  const isStreaming = message.parts.some(
    (part) => part.type === "text" && part.state === "streaming",
  );
  const isPending = isRetrieving || isStreaming;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4 border-b border-border pb-3">
        <h2 className="font-editorial text-[1.55rem] font-semibold tracking-[-0.025em] text-foreground">
          {isPending ? "Generando respuesta" : "Respuesta verificada"}
        </h2>
        {!isPending && citations.length ? (
          <span className="inline-flex min-h-8 shrink-0 items-center gap-1.5 rounded-lg border border-brand-accent/30 bg-brand-accent/10 px-2.5 text-[11px] font-medium text-foreground">
            <CheckCircleIcon className="size-4" weight="regular" aria-hidden="true" />
            Verificado
          </span>
        ) : null}
      </div>
      <MarkdownCitationResponse
        activeCitationId={activeCitationId}
        active={active}
        citations={citations}
        className="font-editorial text-[1.08rem] leading-8 text-foreground [&_p]:my-0"
        isStreaming={isStreaming}
        onCitationClick={onCitationClick}
        messageId={message.id}
        text={text}
      />
      {!isStreaming && citations.length ? (
        <CitationSummary
          activeCitationId={activeCitationId}
          citations={citations}
          messageId={message.id}
          onCitationClick={onCitationClick}
        />
      ) : null}
    </div>
  );
}

function CitationSummary({
  activeCitationId,
  citations,
  messageId,
  onCitationClick,
}: {
  activeCitationId: string | null;
  citations: Citation[];
  messageId: string;
  onCitationClick: (
    citation: Citation,
    citations: Citation[],
    messageId: string,
  ) => void;
}) {
  return (
    <section aria-label="Fuentes oficiales" className="border-t border-border pt-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="font-editorial text-base font-semibold text-foreground">
            {citations.length} fuentes oficiales
          </h3>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Documentos utilizados para verificar la respuesta.
          </p>
        </div>
        <button
          className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent"
          onClick={() => onCitationClick(citations[0], citations, messageId)}
          type="button"
        >
          Ver las {citations.length} fuentes
          <ArrowRightIcon className="size-3.5" aria-hidden="true" />
        </button>
      </div>
      <div className="mt-3 divide-y divide-border border-y border-border">
        {citations.slice(0, 3).map((citation) => {
          const selected = citation.id === activeCitationId;
          const totalPages = citation.location.totalPages;
          return (
            <button
              aria-current={selected ? "true" : undefined}
              className={cn(
                "group/source flex min-h-14 w-full items-center gap-3 px-1 py-2.5 text-left transition-colors hover:bg-muted/55 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand-accent",
                selected && "bg-brand-accent/8",
              )}
              key={citation.id}
              onClick={() => onCitationClick(citation, citations, messageId)}
              type="button"
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-brand-accent/45 bg-brand-accent/6 text-[11px] font-semibold text-brand-accent">
                {citation.label.replace(/^S/, "")}
              </span>
              <FileTextIcon className="size-4 shrink-0 text-muted-foreground" weight="regular" aria-hidden="true" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-semibold text-foreground">
                  {citation.source.filename}
                </span>
                <span className="mt-0.5 block text-[10px] text-muted-foreground">
                  {getCitationDocumentType(citation.source.filename)} · Página {citation.location.pageLabel ?? citation.location.page}
                  {totalPages ? ` de ${totalPages}` : ""}
                </span>
              </span>
              <ArrowRightIcon className="size-3.5 shrink-0 text-muted-foreground transition-transform group-hover/source:translate-x-0.5" aria-hidden="true" />
            </button>
          );
        })}
      </div>
    </section>
  );
}
