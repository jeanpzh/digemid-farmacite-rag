"use client";

import { ChevronDownIcon, MonitorIcon, MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { PipelineTest } from "@/components/workspace/pipeline-test";
import { setRagasDefault, useRagasDefault } from "@/hooks/use-ragas-default";
import { pipelineSchema, type Pipeline } from "@/lib/validation/pipeline";

const themeOptions = [
  { value: "system", label: "Sistema", icon: MonitorIcon },
  { value: "light", label: "Claro", icon: SunIcon },
  { value: "dark", label: "Oscuro", icon: MoonIcon },
] as const;

const modelLabels = {
  answer: "Modelo de respuesta",
  router: "Enrutador de consultas",
  embeddings: "Modelo de embeddings",
  judge: "Juez RAGAS",
} as const;

const providerLabels: Record<string, string> = {
  bedrock: "Amazon Bedrock",
  groq: "Groq",
  ollama: "Ollama",
};

const formatNumber = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 6 });
const subscribeToNothing = () => () => {};

type PipelineState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; pipeline: Pipeline };

export function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const isMounted = useSyncExternalStore(subscribeToNothing, () => true, () => false);
  const ragasDefault = useRagasDefault();
  const [pipelineState, setPipelineState] = useState<PipelineState>({ status: "loading" });
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPipeline() {
      try {
        const response = await fetch("/api/v1/configuration/pipeline", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const pipeline = pipelineSchema.parse(await response.json());
        if (!controller.signal.aborted) setPipelineState({ status: "ready", pipeline });
      } catch {
        if (!controller.signal.aborted) setPipelineState({ status: "error" });
      }
    }

    void loadPipeline();
    return () => controller.abort();
  }, [requestVersion]);

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col overflow-hidden bg-background">
      <header className="flex h-15 shrink-0 items-center border-b border-border bg-card/65 px-5 md:px-7">
        <h1 className="text-sm font-semibold tracking-[-0.02em]">Configuración</h1>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-5">
          <fieldset
            aria-labelledby="appearance-title"
            className="m-0 min-w-0 rounded-2xl border border-border bg-card p-4 md:p-6"
            disabled={!isMounted}
          >
            <h2 id="appearance-title" className="font-editorial text-xl font-semibold">Apariencia</h2>
            <p className="mt-1 text-sm text-muted-foreground">El tema se guarda en este navegador.</p>
            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              {themeOptions.map(({ value, label, icon: Icon }) => (
                <label
                  className="flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-border bg-background px-3 text-sm font-medium hover:bg-muted has-checked:border-ring has-checked:bg-accent has-checked:text-accent-foreground has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ring"
                  key={value}
                >
                  <input
                    checked={(isMounted ? theme ?? "system" : "system") === value}
                    className="sr-only"
                    name="workspace-theme"
                    onChange={() => setTheme(value)}
                    type="radio"
                    value={value}
                  />
                  <Icon aria-hidden="true" className="size-4 shrink-0" />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>

          <section aria-labelledby="chat-evaluation-title" className="rounded-2xl border border-border bg-card p-4 md:p-6">
            <h2 id="chat-evaluation-title" className="font-editorial text-xl font-semibold">Evaluación en chat</h2>
            <div className="mt-4 flex items-start justify-between gap-5">
              <div>
                <p id="ragas-default-label" className="text-sm font-medium">Activar RAGAS por defecto</p>
                <p id="ragas-default-description" className="mt-1 text-sm text-muted-foreground">
                  Se aplica a las conversaciones nuevas. Puedes cambiarlo desde el chat para esa conversación.
                  La evaluación se ejecuta después de la respuesta y hace llamadas adicionales al modelo.
                </p>
              </div>
              <Switch
                aria-describedby="ragas-default-description"
                aria-labelledby="ragas-default-label"
                checked={ragasDefault}
                className="mt-0.5 border-border"
                onCheckedChange={setRagasDefault}
              />
            </div>
          </section>

          <section aria-labelledby="pipeline-title" className="rounded-2xl border border-border bg-card p-4 md:p-6">
            <h2 id="pipeline-title" className="font-editorial text-xl font-semibold">Pipeline activo</h2>
            <p className="mt-1 text-sm text-muted-foreground">Configuración del servicio en ejecución. Solo lectura.</p>

            {pipelineState.status === "loading" ? (
              <p className="mt-4 text-sm text-muted-foreground" role="status">Cargando configuración…</p>
            ) : null}

            {pipelineState.status === "error" ? (
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-background p-3">
                <p className="text-sm text-muted-foreground" role="alert">No se pudo cargar el pipeline activo.</p>
                <Button
                  onClick={() => {
                    setPipelineState({ status: "loading" });
                    setRequestVersion((current) => current + 1);
                  }}
                  type="button"
                  variant="outline"
                >
                  Reintentar
                </Button>
              </div>
            ) : null}

            {pipelineState.status === "ready" ? <PipelineDetails pipeline={pipelineState.pipeline} /> : null}
          </section>
          {pipelineState.status === "ready" ? (
            <PipelineTest active={pipelineState.pipeline.retrieval} limits={pipelineState.pipeline.trial_limits} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

function PipelineDetails({ pipeline }: { pipeline: Pipeline }) {
  const { retrieval } = pipeline;
  const retrievalRows = [
    ["Distancia máxima", retrieval.max_distance],
    ["Resultados mínimos", retrieval.min_results],
    ["Límite de consultas de expansión", retrieval.expansion_max_queries],
  ] as const;

  return (
    <>
      <dl className="mt-4 divide-y divide-border">
        {Object.entries(modelLabels).map(([key, label]) => {
          const { model, provider } = pipeline[key as keyof typeof modelLabels];

          return (
            <div className="grid gap-1 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] sm:gap-4" key={key}>
              <dt className="text-sm font-medium">{label}</dt>
              <dd className="min-w-0">
                <p className="wrap-anywhere font-mono text-xs leading-5">{model}</p>
                <p className="text-xs text-muted-foreground">{providerLabels[provider] ?? provider}</p>
              </dd>
            </div>
          );
        })}
      </dl>
      <details className="group mt-2 rounded-lg border border-border bg-background">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between rounded-lg px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
          Recuperación
          <ChevronDownIcon aria-hidden="true" className="size-4 text-muted-foreground group-open:rotate-180" />
        </summary>
        <dl className="grid gap-3 border-t border-border p-3 sm:grid-cols-3">
          {retrievalRows.map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="mt-1 font-mono text-sm">{formatNumber.format(value)}</dd>
            </div>
          ))}
        </dl>
      </details>
    </>
  );
}
