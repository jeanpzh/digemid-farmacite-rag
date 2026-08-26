"use client";

import {
  ArrowLeftIcon,
  ArrowUpRightIcon,
  FileTextIcon,
  PillIcon,
  ShieldCheckIcon,
  TagsIcon,
} from "lucide-react";
import { useRef, useState } from "react";

import { BrandLogo } from "@/components/brand-logo";
const topics = [
  {
    icon: FileTextIcon,
    label: "Buscar un medicamento",
    questions: [
      "¿El ibuprofeno 200 mg está incluido como medicamento de venta sin receta?",
      "¿Qué presentaciones de paracetamol figuran en el listado de venta sin receta?",
      "¿El diclofenaco dietilamina en gel es de venta sin receta?",
    ],
  },
  {
    icon: ShieldCheckIcon,
    label: "Uso e indicaciones",
    questions: [
      "¿Para qué se usa el diclofenaco sódico en gel?",
      "¿Cuáles son las indicaciones de naproxeno 275 mg?",
      "¿Qué precauciones tiene el clotrimazol 1%?",
    ],
  },
  {
    icon: TagsIcon,
    label: "Presentación y concentración",
    questions: [
      "¿Qué concentración y forma farmacéutica tiene el ibuprofeno de venta sin receta?",
      "¿Qué presentaciones de simeticona están disponibles?",
      "¿Qué formulaciones de paracetamol aparecen en el listado?",
    ],
  },
  {
    icon: PillIcon,
    label: "Advertencias y rotulado",
    questions: [
      "¿Qué advertencias contiene la ficha técnica de paracetamol 500 mg?",
      "¿Qué dice el inserto sobre el uso de ácido acetilsalicílico?",
      "¿Qué precauciones se indican para medicamentos de venta sin receta?",
    ],
  },
];

export function ChatWelcome({
  onSuggestedQuestion,
}: {
  onSuggestedQuestion: (question: string) => void;
}) {
  const [activeTopic, setActiveTopic] = useState<number | null>(null);
  const firstTopicRef = useRef<HTMLButtonElement>(null);
  const topicHeadingRef = useRef<HTMLHeadingElement>(null);
  const selectedTopic = activeTopic === null ? null : topics[activeTopic];

  function showTopic(index: number) {
    setActiveTopic(index);
    window.requestAnimationFrame(() => topicHeadingRef.current?.focus());
  }

  function showAllTopics() {
    setActiveTopic(null);
    window.requestAnimationFrame(() => firstTopicRef.current?.focus());
  }

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center py-12 md:py-16">
      <div className="max-w-2xl">
        <BrandLogo
          aria-hidden="true"
          className="mb-6 size-10 rounded-xl"
        />
        <p className="text-[11px] font-semibold tracking-[0.2em] text-secondary-foreground uppercase">
          Consulta documental
        </p>
        <h2 className="mt-3 text-balance font-editorial text-3xl font-semibold tracking-[-0.045em] text-foreground md:text-[2.75rem] md:leading-[1.05]">
          ¿Qué medicamento o norma necesita revisar?
        </h2>
        <p className="mt-4 max-w-xl text-pretty text-sm leading-6 text-muted-foreground md:text-base">
          Consulte fichas técnicas, indicaciones y advertencias respaldadas por
          documentación oficial de DIGEMID.
        </p>
      </div>
      {selectedTopic ? (
        <div className="pt-8">
          <button
            className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary-foreground"
            onClick={showAllTopics}
            type="button"
          >
            <ArrowLeftIcon className="size-4" aria-hidden="true" />
            Todos los temas
          </button>
          <h3
            className="mt-6 text-xl font-semibold tracking-[-0.03em] focus:outline-none"
            ref={topicHeadingRef}
            tabIndex={-1}
          >
            {selectedTopic.label}
          </h3>
          <div className="mt-4 divide-y divide-sidebar-border/60 rounded-xl border border-sidebar-border/60 bg-card/45">
            {selectedTopic.questions.map((question) => (
              <button
                className="group flex w-full items-center justify-between gap-5 px-4 py-4 text-left text-sm leading-6 text-foreground transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-secondary-foreground focus-visible:text-foreground"
                key={question}
                onClick={() => onSuggestedQuestion(question)}
                type="button"
              >
                <span>{question}</span>
                <ArrowUpRightIcon className="size-4 shrink-0 text-muted-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground" />
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="mt-10 grid gap-2 sm:grid-cols-2">
          {topics.map((topic, index) => {
            const Icon = topic.icon;
            return (
              <button
                className="group flex min-h-20 items-center gap-3 rounded-xl border border-border bg-card/70 p-4 text-left shadow-sm transition-[background-color,border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-brand-accent/60 hover:bg-secondary hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent"
                key={topic.label}
                onClick={() => showTopic(index)}
                ref={index === 0 ? firstTopicRef : undefined}
                type="button"
              >
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-secondary-foreground/10 text-secondary-foreground transition-[background-color,color] duration-200 group-hover:bg-brand-accent group-hover:text-brand-accent-foreground">
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <span className="flex min-w-0 flex-1 items-center justify-between gap-3 text-sm font-medium">
                  <span className="truncate">{topic.label}</span>
                  <ArrowUpRightIcon className="size-4 shrink-0 text-muted-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-secondary-foreground" />
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
