"use client";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import { ChainOfThought } from "@/components/ai-elements/chain-of-thought";
import { CiteMarker } from "@/components/query/cite-marker";
import { QueryForm } from "@/components/query/query-form";
import type { QueryMessage } from "@/hooks/use-query-controller";
import type { Citation, QueryStatus } from "@/lib/validation/query";
import { motion } from "motion/react";
import { MessageSquareIcon, FileSearchIcon } from "lucide-react";
import {
  citationLabelFromHref,
  citationRemarkPlugin,
} from "@/lib/citation-markdown";

type ChatPaneProps = {
  messages: QueryMessage[];
  activeCiteId: string | null;
  onCiteClick: (id: string, citations: Citation[]) => void;
};

function isTextPart(  part: QueryMessage["parts"][number],
): part is Extract<QueryMessage["parts"][number], { type: "text" }> {
  return part.type === "text";
}

function isStatusPart(
  part: QueryMessage["parts"][number],
): part is { type: "data-status"; data: QueryStatus } {
  return part.type === "data-status";
}

function isCitationsPart(
  part: QueryMessage["parts"][number],
): part is { type: "data-citation"; data: Citation } {
  return part.type === "data-citation";
}

function statusLabel(status: QueryStatus) {
  return status.label;
}

function CitationResponse({
  text,
  citations,
  activeCiteId,
  onCiteClick,
  isStreaming,
}: {
  text: string;
  citations: Citation[];
  activeCiteId: string | null;
  onCiteClick: (id: string, citations: Citation[]) => void;
  isStreaming: boolean;
}) {
  const citationByLabel = new Map(
    citations.map((citation) => [citation.label, citation]),
  );

  return (
    <MessageResponse
      components={{
        a: ({ children, href, node: _node, ...props }) => {
          void _node;
          const label = citationLabelFromHref(href);
          const citation = label ? citationByLabel.get(label) : undefined;

          if (!citation) {
            return (
              <a href={href} {...props}>
                {children}
              </a>
            );
          }

          return (
            <CiteMarker
              active={activeCiteId === citation.id}
              id={citation.id}
              label={citation.label}
              onClick={() => onCiteClick(citation.id, citations)}
              excerpt={citation.excerpt}
              filename={citation.source.filename}
              page={citation.location.pageLabel ?? citation.location.page}
              url={citation.source.url}
            />
          );
        },
      }}
      isAnimating={isStreaming}
      remarkPlugins={[citationRemarkPlugin(new Set(citations.map((citation) => citation.label)))]}
    >
      {text}
    </MessageResponse>
  );
}

function StatusPart({ status }: { status: QueryStatus }) {
  return (
    <ChainOfThought defaultOpen className="not-prose">
      <p className="text-xs text-muted-foreground">
        <FileSearchIcon className="mr-1 inline size-3.5 align-[-2px]" />
        {statusLabel(status)}
      </p>
    </ChainOfThought>
  );
}

function AssistantMessage({
  message,
  activeCiteId,
  onCiteClick,
}: {
  message: QueryMessage;
  activeCiteId: string | null;
  onCiteClick: (id: string, citations: Citation[]) => void;
}) {
  const citations = message.parts
    .filter(isCitationsPart)
    .map((part) => part.data)
    .filter(
      (citation, index, all) =>
        all.findIndex((item) => item.id === citation.id) === index,
    );
  const text = message.parts.filter(isTextPart).map((part) => part.text).join("");
  const statuses = message.parts.filter(isStatusPart);
  const isStreaming = message.parts.some(
    (part) => part.type === "text" && part.state === "streaming",
  );

  return (
    <div className="flex w-full flex-col gap-3">
      {statuses.map((status, index) => (
        <StatusPart key={index} status={status.data} />
      ))}
      {text ? (
        <CitationResponse
          activeCiteId={activeCiteId}
          citations={citations}
          isStreaming={isStreaming}
          onCiteClick={onCiteClick}
          text={text}
        />
      ) : null}
    </div>
  );
}

export function ChatPane({
  messages,
  activeCiteId,
  onCiteClick,
}: ChatPaneProps) {
  return (
    <motion.div
      className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden max-h-screen"
      layout
    >
      <Conversation aria-label="Conversación" className="min-h-0 flex-1">
        <ConversationContent className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
          {messages.length === 0 ? (
            <ConversationEmptyState
              description="Consulte documentos regulatorios y obtenga respuestas a sus preguntas."
              icon={<MessageSquareIcon className="size-8" />}
              title="Bienvenido a DIGEMID RAG"
            />
          ) : (
            messages.map((message) => (
              <Message from={message.role} key={message.id}>
                <MessageContent className="max-w-full">
                  {message.role === "assistant" ? (
                    <AssistantMessage
                      activeCiteId={activeCiteId}
                      message={message}
                      onCiteClick={onCiteClick}
                    />
                  ) : (
                    <MessageResponse isAnimating={false}>
                      {message.parts
                        .filter(isTextPart)
                        .map((part) => part.text)
                        .join("")}
                    </MessageResponse>
                  )}
                </MessageContent>
              </Message>
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>
      <QueryForm />
    </motion.div>
  );
}
