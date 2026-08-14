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
} from "@/components/ai-elements/message";
import { useQueryContext } from "@/components/query/query-provider";
import type { ReactNode } from "react";
import { MessageSquareIcon } from "lucide-react";

function messageText(parts: { type: string; text?: string }[]): string {
  return parts
    .filter((part) => part.type === "text")
    .map((part) => part.text ?? "")
    .join("");
}

export function QueryOutput({ initialInput }: { initialInput?: ReactNode }) {
  const {
    state: { messages },
  } = useQueryContext();

  return (
    <Conversation
      aria-label="Conversación"
      aria-live="polite"
    >
      <ConversationContent>
        {messages.length === 0 ? (
          <ConversationEmptyState
            title="Bienvenido a DIGEMID RAG"
            description="Consulte documentos regulatorios y obtenga respuestas a sus preguntas."
          />
        ) : (
          messages.map((message, index) => (
            <Message
              from={message.role}
              key={index}
            >
              <MessageContent>
                {messageText(message.parts)}
              </MessageContent>
            </Message>
          ))
        )}
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>
  );
}
