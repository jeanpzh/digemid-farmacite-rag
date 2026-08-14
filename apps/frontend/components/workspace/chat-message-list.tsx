"use client";

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
import type { RetrievalStatus } from "@/lib/validation/rag-stream";
import type { Citation } from "@/lib/validation/rag-stream";

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
      <ConversationContent className="mx-auto w-full max-w-3xl gap-10 px-0 pt-8 pb-36 md:pt-12 md:pb-40">
        {messages.map((message, messageIndex) => (
          <Message
            key={message.id}
            from={message.role}
            className="reveal-on-load max-w-[min(100%,48rem)]"
          >
            <MessageContent className="text-[0.95rem] leading-7">
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
  onCitationClick,
}: {
  active: boolean;
  activeCitationId: string | null;
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

  return (
    <MarkdownCitationResponse
      activeCitationId={activeCitationId}
      active={active}
      citations={citations}
      isStreaming={isStreaming}
      onCitationClick={onCitationClick}
      messageId={message.id}
      text={text}
    />
  );
}
