"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import type { UIMessage } from "ai";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  ragDataPartSchemas,
  type Citation,
  type RagDataParts,
  type RetrievalStatus,
} from "@/lib/validation/rag-stream";

export type ChatMetadata = { status?: string };

export type ChatMessage = UIMessage<ChatMetadata, RagDataParts>;

type WorkspaceContextValue = {
  conversationId: string;
  messages: ChatMessage[];
  citations: Citation[];
  retrievalStatus: RetrievalStatus | null;
  status: "submitted" | "streaming" | "ready" | "error";
  error?: Error;
  isLoading: boolean;
  input: string;
  setInput: (value: string) => void;
  submitQuestion: (question: string) => void;
  startNewConversation: () => void;
  stop: () => void;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

const transport = new DefaultChatTransport<ChatMessage>({
  api: "/api/v1/chat",
  prepareSendMessagesRequest({ messages, body }) {
    return {
      body: {
        ...body,
        messages: messages
          .slice(-7)
          .map(({ id, role, parts }) => ({
            id,
            role,
            parts: parts.flatMap((part) =>
              part.type === "text" ? [{ text: part.text, type: "text" }] : [],
            ),
          }))
          .filter((message) => message.parts.length > 0),
      },
    };
  },
});

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [conversationId, setConversationId] = useState(() =>
    crypto.randomUUID(),
  );
  const [input, setInput] = useState("");
  const [retrievalStatus, setRetrievalStatus] =
    useState<RetrievalStatus | null>(null);
  const { messages, sendMessage, setMessages, stop, status, error } =
    useChat<ChatMessage>({
      transport,
      throttle: 50,
      dataPartSchemas: ragDataPartSchemas as never,
      onData(dataPart) {
        if (dataPart.type === "data-status") {
          setRetrievalStatus(dataPart.data);
        }
      },
      onError() {
        setRetrievalStatus(null);
      },
    });

  const isLoading = status === "streaming" || status === "submitted";
  const citations = getCitations(messages);

  useEffect(() => {
    if (!isLoading) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [isLoading, messages.length]);

  function submitQuestion(question: string) {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) {
      return;
    }

    setRetrievalStatus(null);
    sendMessage(
      { text: trimmedQuestion },
      { body: { requestId: crypto.randomUUID() } },
    );
    setInput("");
  }

  function startNewConversation() {
    if (isLoading) {
      stop();
    }
    setMessages([]);
    setConversationId(crypto.randomUUID());
    setRetrievalStatus(null);
    setInput("");
  }

  function stopConversation() {
    stop();
    setRetrievalStatus(null);
  }

  return (
    <WorkspaceContext.Provider
      value={{
        conversationId,
        messages,
        citations,
        retrievalStatus,
        status,
        error,
        isLoading,
        input,
        setInput,
        submitQuestion,
        startNewConversation,
        stop: stopConversation,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within WorkspaceProvider");
  }
  return context;
}

function getCitations(messages: ChatMessage[]) {
  const citations = new Map<string, Citation>();
  for (const message of messages) {
    for (const part of message.parts) {
      if (part.type === "data-citation") {
        citations.set(part.data.id, part.data);
      }
    }
  }
  return [...citations.values()];
}
