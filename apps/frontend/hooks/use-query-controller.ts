"use client";

import { useChat } from "@ai-sdk/react";
import {
  DefaultChatTransport,
  type ChatStatus,
  type UIMessage,
} from "ai";

import {
  queryDataPartSchemas,
  type QueryDataParts,
} from "@/lib/validation/query";

export type QueryMessage = UIMessage<unknown, QueryDataParts>;

export type QueryControllerState = {
  error: string | null;
  messages: QueryMessage[];
  status: ChatStatus;
};

function latestUserText(messages: QueryMessage[]): string {
  for (let index = messages.length - 1; index >= 0; index--) {
    const message = messages[index];
    if (message.role !== "user") continue;
    return message.parts
      .filter((part) => part.type === "text")
      .map((part) => (part.type === "text" ? part.text : ""))
      .join("");
  }
  return "";
}

const transport = new DefaultChatTransport<QueryMessage>({
  api: "/api/query",
  prepareSendMessagesRequest({ messages }) {
    return { body: { question: latestUserText(messages) } };
  },
});

export function useQueryController() {
  const { error, messages, sendMessage, status, stop } = useChat<QueryMessage>({
    transport,
    dataPartSchemas: queryDataPartSchemas as never,
  });

  const state: QueryControllerState = {
    error: error ? error.message : null,
    messages,
    status,
  };

  function submitQuestion(question: string) {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || status !== "ready") return;
    void sendMessage({ text: trimmedQuestion });
  }

  return { state, isPending: status !== "ready", submitQuestion, stop };
}
