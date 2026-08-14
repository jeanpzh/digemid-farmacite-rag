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
    <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center py-10 md:py-16">
      <div className="border-b border-sidebar-border/70 pb-8">
        <BrandLogo
          aria-hidden="true"
          className="mb-5 size-11 rounded-xl"
        />
        <p className="text-xs font-medium tracking-[0.12em] text-secondary-foreground uppercase">
          Consulta documental
        </p>
        <h2 className="mt-3 text-balance text-3xl font-semibold tracking-[-0.045em] text-foreground md:text-4xl">
          ¿Qué necesita revisar?
        </h2>
        <p className="mt-3 max-w-xl text-pretty text-sm leading-6 text-muted-foreground md:text-base">
          Elija un tema para ver consultas frecuentes o escriba su propia pregunta.
        </p>
      </div>
      {selectedTopic ? (
        <div className="pt-6">
          <button
            className="inline-flex min-h-8 items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground focus-visible:underline"
            onClick={showAllTopics}
            type="button"
          >
            <ArrowLeftIcon className="size-4" aria-hidden="true" />
            Todos los temas
          </button>
          <h3
            className="mt-5 text-xl font-semibold tracking-[-0.025em] focus:outline-none"
            ref={topicHeadingRef}
            tabIndex={-1}
          >
            {selectedTopic.label}
          </h3>
          <div className="mt-4 divide-y divide-sidebar-border/70 border-y border-sidebar-border/70">
            {selectedTopic.questions.map((question) => (
              <button
                className="group flex w-full items-center justify-between gap-5 py-4 text-left text-sm leading-6 text-foreground transition-colors hover:text-secondary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-secondary-foreground focus-visible:text-secondary-foreground"
                key={question}
                onClick={() => onSuggestedQuestion(question)}
                type="button"
              >
                <span>{question}</span>
                <ArrowUpRightIcon className="size-4 shrink-0 text-muted-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-secondary-foreground" />
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid gap-px overflow-hidden border border-sidebar-border/70 bg-sidebar-border/70 sm:grid-cols-2">
          {topics.map((topic, index) => {
            const Icon = topic.icon;
            return (
              <button
                className="group flex min-h-32 flex-col items-start justify-between bg-background p-5 text-left transition-colors hover:bg-sidebar-accent/65 focus-visible:bg-sidebar-accent/65"
                key={topic.label}
                onClick={() => showTopic(index)}
                ref={index === 0 ? firstTopicRef : undefined}
                type="button"
              >
                <Icon className="size-5 text-secondary-foreground" aria-hidden="true" />
                <span className="flex w-full items-center justify-between gap-3 text-sm font-medium">
                  {topic.label}
                  <ArrowUpRightIcon className="size-4 text-muted-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-secondary-foreground" />
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
