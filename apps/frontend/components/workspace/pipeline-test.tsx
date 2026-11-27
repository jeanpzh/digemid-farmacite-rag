"use client";

import { FlaskConicalIcon } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  trialEventSchema,
  type PipelineRetrieval,
  type TrialResult,
} from "@/lib/validation/pipeline";

const fields = [
  { key: "max_distance", label: "Distancia máxima", min: 0, step: "any" },
  { key: "min_results", label: "Resultados mínimos", min: 1, step: 1 },
  { key: "expansion_max_queries", label: "Límite de consultas de expansión", min: 0, step: 1 },
] as const;

const metrics = [
  ["avg_faithfulness", "Fidelidad", false],
  ["avg_context_precision", "Precisión del contexto", false],
  ["avg_context_recall", "Cobertura del contexto", false],
  ["avg_response_relevancy", "Relevancia de la respuesta", false],
  ["refusal_accuracy", "Rechazos correctos", false],
  ["avg_retrieval_ms", "Recuperación promedio", true],
  ["p95_retrieval_ms", "Recuperación p95", true],
  ["avg_ttft_ms", "Primer token tras recuperación", true],
] as const;

const errorMessages = {
  busy: "Ya hay una prueba en curso. Inténtalo cuando termine.",
  timeout: "La prueba superó el tiempo límite. Inténtalo de nuevo.",
  failed: "No se pudo completar la prueba. Inténtalo de nuevo.",
};

const numberFormat = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 });
const percentFormat = new Intl.NumberFormat("es-PE", { style: "percent", maximumFractionDigits: 1 });
const deltaFormat = new Intl.NumberFormat("es-PE", {
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});

type TrialState =
  | { status: "idle" }
  | { status: "running"; completed: number; total: number }
  | { status: "error"; message: string }
  | { status: "cancelled" }
  | { status: "ready"; result: TrialResult };

export function PipelineTest({
  active,
  limits,
}: {
  active: PipelineRetrieval;
  limits: PipelineRetrieval;
}) {
  const [state, setState] = useState<TrialState>({ status: "idle" });
  const currentRun = useRef<AbortController | null>(null);
  const running = state.status === "running";

  useEffect(() => () => currentRun.current?.abort(), []);

  async function runTest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (currentRun.current) return;

    const data = new FormData(event.currentTarget);
    const candidate = {
      max_distance: Number(data.get("max_distance")),
      min_results: Number(data.get("min_results")),
      expansion_max_queries: Number(data.get("expansion_max_queries")),
    };
    const controller = new AbortController();
    currentRun.current = controller;
    setState({ status: "running", completed: 0, total: 0 });

    try {
      const response = await fetch("/api/v1/configuration/pipeline/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(candidate),
        signal: controller.signal,
      });
      if (response.status === 429) {
        setState({ status: "error", message: "Se alcanzó el límite de pruebas. Espera un minuto." });
        return;
      }
      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      let pending = "";
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) throw new Error("Incomplete pipeline test");

          const lines = (pending + value).split("\n");
          pending = lines.pop() ?? "";
          for (const line of lines) {
            if (controller.signal.aborted) return;
            const update = trialEventSchema.parse(JSON.parse(line));
            if (update.type === "progress") {
              setState({ status: "running", completed: update.completed, total: update.total });
            } else {
              setState(update.type === "result"
                ? { status: "ready", result: update }
                : { status: "error", message: errorMessages[update.code] });
              return;
            }
          }
        }
      } finally {
        void reader.cancel().catch(() => {});
        reader.releaseLock();
      }
    } catch {
      if (!controller.signal.aborted) {
        setState({ status: "error", message: errorMessages.failed });
      }
    } finally {
      if (currentRun.current === controller) currentRun.current = null;
    }
  }

  function cancelTest() {
    currentRun.current?.abort();
    currentRun.current = null;
    setState({ status: "cancelled" });
  }

  return (
    <section aria-labelledby="pipeline-test-title" className="rounded-2xl border border-border bg-card p-4 md:p-6">
      <div className="flex items-center gap-2">
        <FlaskConicalIcon aria-hidden="true" className="size-4 text-muted-foreground" />
        <h2 id="pipeline-test-title" className="font-editorial text-xl font-semibold">Modo de prueba</h2>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Compara ajustes de recuperación con el pipeline activo sobre el conjunto dorado de DIGEMID.
        Los cambios solo se usan en esta prueba.
      </p>

      <form
        className="mt-4"
        onChange={() => setState({ status: "idle" })}
        onReset={() => setState({ status: "idle" })}
        onSubmit={runTest}
      >
        <fieldset className="grid min-w-0 gap-3 sm:grid-cols-3" disabled={running}>
          <legend className="sr-only">Ajustes de recuperación para la prueba</legend>
          {fields.map(({ key, label, min, step }) => (
            <label className="flex min-w-0 flex-col gap-1.5 text-sm font-medium" key={key}>
              {label}
              <Input
                className="bg-background font-mono"
                defaultValue={active[key]}
                max={limits[key]}
                min={min}
                name={key}
                required
                step={step}
                type="number"
              />
            </label>
          ))}
        </fieldset>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button disabled={running} type="submit">Ejecutar prueba</Button>
          {running ? (
            <Button onClick={cancelTest} type="button" variant="outline">Cancelar</Button>
          ) : (
            <Button type="reset" variant="outline">Restablecer valores activos</Button>
          )}
        </div>
      </form>

      {state.status === "running" ? (
        <div className="mt-4">
          <p className="text-sm text-muted-foreground" role="status">
            {state.total > 0 ? `${state.completed} de ${state.total} casos evaluados` : "Preparando la prueba…"}
          </p>
          <progress
            aria-label="Progreso de la prueba"
            className="mt-2 block h-2 w-full accent-primary"
            max={state.total || 1}
            value={state.total ? state.completed : undefined}
          />
        </div>
      ) : null}
      {state.status === "cancelled" ? <p className="mt-4 text-sm text-muted-foreground" role="status">Prueba cancelada.</p> : null}
      {state.status === "error" ? <p className="mt-4 text-sm text-destructive" role="alert">{state.message}</p> : null}
      {state.status === "ready" ? <TestComparison result={state.result} /> : null}
    </section>
  );
}

function formatMetric(value: number | null, latency: boolean) {
  if (value === null) return "—";
  return latency ? `${numberFormat.format(value)} ms` : percentFormat.format(value);
}

function TestComparison({ result }: { result: TrialResult }) {
  return (
    <div className="mt-5 overflow-x-auto">
      <table className="w-full border-collapse text-left text-xs sm:text-sm">
        <caption className="pb-2 text-left text-sm font-medium">
          Comparación · {result.sample_count} casos de {result.dataset}
        </caption>
        <thead className="border-b border-border text-muted-foreground">
          <tr>
            <th className="py-2 pr-2" scope="col">Métrica</th>
            <th className="px-1.5 py-2 text-right" scope="col">Activo</th>
            <th className="px-1.5 py-2 text-right" scope="col">Prueba</th>
            <th className="py-2 pl-1.5 text-right" scope="col">Cambio</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {metrics.map(([key, label, latency]) => {
            const baseline = result.baseline[key];
            const candidate = result.candidate[key];
            const delta = baseline === null || candidate === null ? null : (candidate - baseline) * (latency ? 1 : 100);

            return (
              <tr key={key}>
                <th className="py-2 pr-2 font-medium" scope="row">{label}</th>
                <td className="whitespace-nowrap px-1.5 py-2 text-right tabular-nums">{formatMetric(baseline, latency)}</td>
                <td className="whitespace-nowrap px-1.5 py-2 text-right tabular-nums">{formatMetric(candidate, latency)}</td>
                <td className="whitespace-nowrap py-2 pl-1.5 text-right tabular-nums">
                  {delta === null ? "—" : `${deltaFormat.format(delta)} ${latency ? "ms" : "pp"}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
