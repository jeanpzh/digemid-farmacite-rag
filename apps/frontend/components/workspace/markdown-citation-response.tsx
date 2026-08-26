"use client";

import { CitationPart } from "@/components/workspace/citation-part";
import type { ChatMessage } from "@/components/workspace/workspace-provider";
import type { Citation } from "@/lib/validation/rag-stream";
import {
  citationLabelFromHref,
  citationRemarkPlugin,
} from "@/lib/citation-markdown";
import { MessageResponse } from "@/components/ai-elements/message";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type TextPart = Extract<ChatMessage["parts"][number], { type: "text" }>;
type CitationPartData = Extract<
  ChatMessage["parts"][number],
  { type: "data-citation" }
>;

export function MarkdownCitationResponse({
  citations,
  isStreaming,
  active,
  activeCitationId,
  className,
  onCitationClick,
  messageId,
  text,
}: {
  active: boolean;
  activeCitationId: string | null;
  className?: string;
  citations: Citation[];
  isStreaming: boolean;
  onCitationClick: (
    citation: Citation,
    citations: Citation[],
    messageId: string,
  ) => void;
  messageId: string;
  text: string;
}) {
  const citationByLabel = new Map(
    citations.map((citation) => [citation.label, citation]),
  );

  return (
    <MessageResponse
      className={cn(className)}
      components={{
        a: ({ children, href, node: _node, ...props }) => {
          void _node;
          const label = citationLabelFromHref(href);
          const citation = label ? citationByLabel.get(label) : undefined;
          return citation ? (
            <CitationPart
              active={active && activeCitationId === citation.id}
              citation={citation}
              onClick={() => onCitationClick(citation, citations, messageId)}
            />
          ) : (
            <a href={href} {...props}>
              {children as ReactNode}
            </a>
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

export function getAssistantText(parts: ChatMessage["parts"]) {
  return parts
    .filter((part): part is TextPart => part.type === "text")
    .map((part) => part.text)
    .join("");
}

export function getAssistantCitations(parts: ChatMessage["parts"]) {
  const citations = new Map<string, Citation>();
  for (const part of parts) {
    if (part.type !== "data-citation") {
      continue;
    }
    const citationPart: CitationPartData = part;
    citations.set(citationPart.data.label, citationPart.data);
  }
  return [...citations.values()];
}
