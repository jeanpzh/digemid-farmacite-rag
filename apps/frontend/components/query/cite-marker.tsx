"use client";

import {
  InlineCitation,
  InlineCitationCard,
  InlineCitationCardBody,
  InlineCitationCardTrigger,
  InlineCitationCarousel,
  InlineCitationCarouselContent,
  InlineCitationCarouselItem,
  InlineCitationSource,
  InlineCitationQuote,
} from "@/components/ai-elements/inline-citation";

type CiteMarkerProps = {
  id: string;
  label?: string;
  active: boolean;
  onClick: () => void;
  filename?: string;
  url?: string | null;
  excerpt?: string;
  page?: string | number;
};

export function CiteMarker({
  id,
  label = id,
  active,
  onClick,
  filename = "Fuente citada",
  url = null,
  excerpt = "",
  page = "sin página",
}: CiteMarkerProps) {
  return (
    <InlineCitation>
      <InlineCitationCard>
        <InlineCitationCardTrigger
          aria-label={`Abrir fuente ${id}`}
          className={active ? "bg-orange-600 text-white" : ""}
          onClick={onClick}
          sources={url ? [url] : []}
        >
          {label.replace(/^S/, "")}
        </InlineCitationCardTrigger>
        <InlineCitationCardBody>
          <InlineCitationCarousel>
            <InlineCitationCarouselContent>
              <InlineCitationCarouselItem>
                <InlineCitationSource
                  description={`Página ${page}`}
                  title={`${id} · ${filename}`}
                  url={url ?? undefined}
                />
                <InlineCitationQuote>{excerpt}</InlineCitationQuote>
              </InlineCitationCarouselItem>
            </InlineCitationCarouselContent>
          </InlineCitationCarousel>
        </InlineCitationCardBody>
      </InlineCitationCard>
    </InlineCitation>
  );
}
