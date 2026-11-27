"use client";

import {
  CheckCircle2Icon,
  ChevronDownIcon,
  ChevronRightIcon,
  ClockIcon,
  FileTextIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  XCircleIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import {
  evalRunDetailResponseSchema,
  evalRunsResponseSchema,
  type EvalResult,
  type EvalRun,
} from "@/lib/validation/ragas";

const CATEGORY_LABELS: Record<string, string> = {
  all: "Todas",
  standalone: "Standalone",
  followup: "Seguimiento",
  multi_medicine: "Multimedicamento",
  out_of_domain: "Fuera de dominio",
};

function formatPercent(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function formatMs(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value)} ms`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function scoreTone(value: number | null | undefined): string {
  if (value == null) return "bg-muted-foreground/30";
  if (value >= 0.85) return "bg-emerald-700 dark:bg-emerald-400";
  if (value >= 0.65) return "bg-amber-600 dark:bg-amber-400";
  return "bg-rose-700 dark:bg-rose-400";
}

function scoreTextTone(value: number | null | undefined): string {
  if (value == null) return "text-muted-foreground";
  if (value >= 0.85) return "text-emerald-800 dark:text-emerald-300";
  if (value >= 0.65) return "text-amber-800 dark:text-amber-300";
  return "text-rose-800 dark:text-rose-300";
}

export function EvalsPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [results, setResults] = useState<EvalResult[]>([]);
  const [category, setCategory] = useState<string>("all");
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadedRunId, setLoadedRunId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadingDetail = selectedRunId !== null && loadedRunId !== selectedRunId;

  const fetchRuns = useCallback(async () => {
    try {
      const response = await fetch("/api/v1/evaluations/runs?limit=20", {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const parsed = evalRunsResponseSchema.parse(await response.json());
      setError(null);
      setRuns(parsed.runs);
      if (parsed.runs.length > 0) {
        setSelectedRunId((prev) =>
          prev && parsed.runs.some((r) => r.id === prev) ? prev : parsed.runs[0].id,
        );
      } else {
        setSelectedRunId(null);
        setResults([]);
      }
    } catch {
      setError("No se pudieron cargar las evaluaciones RAGAS desde el backend.");
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  const handleRefresh = useCallback(() => {
    setLoadingRuns(true);
    void fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    let active = true;
    fetch("/api/v1/evaluations/runs?limit=20", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return evalRunsResponseSchema.parse(await response.json());
      })
      .then((parsed) => {
        if (!active) return;
        setError(null);
        setRuns(parsed.runs);
        if (parsed.runs.length > 0) {
          setSelectedRunId((prev) =>
            prev && parsed.runs.some((r) => r.id === prev) ? prev : parsed.runs[0].id,
          );
        } else {
          setSelectedRunId(null);
          setResults([]);
        }
      })
      .catch(() => {
        if (active) {
          setError("No se pudieron cargar las evaluaciones RAGAS desde el backend.");
        }
      })
      .finally(() => {
        if (active) setLoadingRuns(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (selectedRunId == null) return;
    let cancelled = false;
    fetch(`/api/v1/evaluations/runs/${selectedRunId}`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return evalRunDetailResponseSchema.parse(await response.json());
      })
      .then((detail) => {
        if (cancelled) return;
        setResults(detail.results);
        setExpandedCaseId(detail.results[0]?.case_id ?? null);
        setLoadedRunId(selectedRunId);
      })
      .catch(() => {
        if (!cancelled) {
          setError("No se pudo cargar el detalle de la corrida seleccionada.");
          setLoadedRunId(selectedRunId);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRunId]);

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? null,
    [runs, selectedRunId],
  );
  const previousRun = useMemo(() => {
    if (selectedRunId == null) return null;
    const index = runs.findIndex((run) => run.id === selectedRunId);
    return index >= 0 && index + 1 < runs.length ? runs[index + 1] : null;
  }, [runs, selectedRunId]);

  const filteredResults = useMemo(
    () =>
      category === "all"
        ? results
        : results.filter((item) => item.category === category),
    [category, results],
  );

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col overflow-hidden bg-background">
      <header className="flex h-15 shrink-0 items-center justify-between gap-4 border-b border-border bg-card/65 px-5 md:px-7">
        <div className="flex min-w-0 items-center gap-3 text-sm">
          <span className="shrink-0 font-medium text-muted-foreground">Evaluaciones</span>
          <span aria-hidden="true" className="text-border">/</span>
          <span className="truncate font-semibold tracking-[-0.02em] text-foreground">
            RAGAS · Calidad y latencia
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2.5">
          {runs.length > 0 ? (
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="hidden sm:inline">Corrida:</span>
              <select
                aria-label="Seleccionar corrida de evaluación"
                className="h-9 rounded-lg border border-border bg-background px-2.5 text-xs font-medium text-foreground focus-visible:outline-2 focus-visible:outline-brand-accent"
                onChange={(event) => setSelectedRunId(Number(event.target.value))}
                value={selectedRunId ?? ""}
              >
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    #{run.id} · {run.name} {run.git_sha ? `(${run.git_sha})` : ""}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <button
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground transition-colors hover:bg-muted"
            onClick={handleRefresh}
            type="button"
          >
            <RefreshCwIcon className={cn("size-3.5", loadingRuns && "animate-spin")} aria-hidden="true" />
            Actualizar
          </button>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-6 md:px-8">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
          {error ? (
            <div
              className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-foreground"
              role="alert"
            >
              {error}
            </div>
          ) : null}

          {!loadingRuns && !selectedRun && !error ? (
            <div className="rounded-2xl border border-border bg-card p-8 text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Sin corridas registradas
              </p>
              <h2 className="mt-2 font-editorial text-2xl font-semibold text-foreground">
                Ejecute su primera evaluación RAGAS
              </h2>
              <p className="mx-auto mt-2 max-w-lg text-sm text-muted-foreground">
                Desde <code className="rounded bg-background px-1.5 py-0.5 font-mono text-xs">apps/backend</code>,
                ejecute <code className="rounded bg-background px-1.5 py-0.5 font-mono text-xs">uv run eval-rag --name baseline</code>{" "}
                para evaluar el conjunto dorado de DIGEMID y registrar métricas en Supabase.
              </p>
            </div>
          ) : null}

          {selectedRun ? (
            <>
              <section aria-label="Resumen de corrida" className="flex flex-wrap items-baseline justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Corrida #{selectedRun.id} · {selectedRun.dataset_name}
                    {selectedRun.git_sha ? ` · commit ${selectedRun.git_sha}` : ""}
                  </p>
                  <h1 className="mt-1 font-editorial text-3xl font-semibold tracking-[-0.025em] text-foreground">
                    {selectedRun.name}
                  </h1>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                  <span className="rounded-md border border-border bg-card px-2 py-1 font-mono">
                    chat: {selectedRun.chat_model}
                  </span>
                  <span className="rounded-md border border-border bg-card px-2 py-1 font-mono">
                    router: {selectedRun.router_model}
                  </span>
                  <span className="rounded-md border border-border bg-card px-2 py-1 font-mono">
                    juez: {selectedRun.judge_model}
                  </span>
                  {selectedRun.created_at ? (
                    <span className="px-1">{formatDate(selectedRun.created_at)}</span>
                  ) : null}
                </div>
              </section>

              <section aria-label="Métricas RAGAS" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                  current={selectedRun.avg_faithfulness}
                  description="Afirmaciones respaldadas estrictamente por los contextos"
                  label="Fidelidad"
                  previous={previousRun?.avg_faithfulness}
                />
                <MetricCard
                  current={selectedRun.avg_context_precision}
                  description="Precisión media de los fragmentos recuperados arriba"
                  label="Precisión de contexto"
                  previous={previousRun?.avg_context_precision}
                />
                <MetricCard
                  current={selectedRun.avg_context_recall}
                  description="Cobertura de la respuesta de referencia DIGEMID"
                  label="Exhaustividad (Recall)"
                  previous={previousRun?.avg_context_recall}
                />
                <MetricCard
                  current={selectedRun.avg_response_relevancy}
                  description="Alineación semántica entre pregunta y respuesta"
                  label="Relevancia de respuesta"
                  previous={previousRun?.avg_response_relevancy}
                />
              </section>

              <section
                aria-label="Métricas operacionales"
                className="grid grid-cols-2 gap-3 rounded-2xl border border-border bg-card/80 p-4 md:grid-cols-4"
              >
                <OperationalStat
                  icon={<ClockIcon className="size-4 text-muted-foreground" aria-hidden="true" />}
                  label="Recuperación promedio"
                  value={formatMs(selectedRun.avg_retrieval_ms)}
                />
                <OperationalStat
                  icon={<ClockIcon className="size-4 text-muted-foreground" aria-hidden="true" />}
                  label="Recuperación p95"
                  value={formatMs(selectedRun.p95_retrieval_ms)}
                />
                <OperationalStat
                  icon={<ClockIcon className="size-4 text-muted-foreground" aria-hidden="true" />}
                  label="TTFT promedio"
                  value={formatMs(selectedRun.avg_ttft_ms)}
                />
                <OperationalStat
                  icon={<ShieldCheckIcon className="size-4 text-muted-foreground" aria-hidden="true" />}
                  label="Rechazo fuera de dominio"
                  value={formatPercent(selectedRun.refusal_accuracy)}
                />
              </section>

              <section aria-label="Casos evaluados" className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-editorial text-xl font-semibold text-foreground">
                      Auditoría por caso ({filteredResults.length} de {results.length})
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      Expanda un caso para inspeccionar afirmaciones verificadas, referencia oficial y fragmentos recuperados.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Filtrar por categoría">
                    {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                      <button
                        aria-selected={category === key}
                        className={cn(
                          "rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors",
                          category === key
                            ? "border-foreground bg-foreground text-background"
                            : "border-border bg-card text-muted-foreground hover:text-foreground",
                        )}
                        key={key}
                        onClick={() => setCategory(key)}
                        role="tab"
                        type="button"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {loadingDetail ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    Cargando detalle de casos…
                  </p>
                ) : (
                  <div className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
                    {filteredResults.map((item) => {
                      const expanded = expandedCaseId === item.case_id;
                      return (
                        <div key={item.id} className="bg-card">
                          <button
                            aria-expanded={expanded}
                            className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-background/60"
                            onClick={() =>
                              setExpandedCaseId(expanded ? null : item.case_id)
                            }
                            type="button"
                          >
                            {expanded ? (
                              <ChevronDownIcon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                            ) : (
                              <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                            )}
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                                  {CATEGORY_LABELS[item.category] ?? item.category}
                                </span>
                                <span className="font-mono text-[11px] text-muted-foreground">
                                  {item.case_id}
                                </span>
                              </div>
                              <p className="mt-1 truncate font-editorial text-[0.98rem] font-medium text-foreground">
                                {item.question}
                              </p>
                            </div>
                            <div className="hidden shrink-0 items-center gap-3 text-xs font-mono sm:flex">
                              {item.category === "out_of_domain" ? (
                                <span
                                  className={cn(
                                    "inline-flex items-center gap-1 rounded-md px-2 py-0.5 font-sans text-xs font-medium",
                                    item.passed_refusal
                                      ? "bg-emerald-700/12 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-300"
                                      : "bg-rose-700/12 text-rose-800 dark:bg-rose-400/15 dark:text-rose-300",
                                  )}
                                >
                                  {item.passed_refusal ? "Rechazado correctamente" : "Fallo de rechazo"}
                                </span>
                              ) : (
                                <>
                                  <ScorePill label="F" value={item.faithfulness} />
                                  <ScorePill label="P" value={item.context_precision} />
                                  <ScorePill label="R" value={item.context_recall} />
                                  <ScorePill label="Rel" value={item.response_relevancy} />
                                </>
                              )}
                              <span className="w-16 text-right text-[11px] text-muted-foreground">
                                {formatMs(item.retrieval_ms)}
                              </span>
                            </div>
                          </button>

                          {expanded ? (
                            <div className="space-y-4 border-t border-border bg-background/60 px-5 py-4">
                              {item.history ? (
                                <div className="rounded-xl border border-border bg-card/70 p-3">
                                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                    Historial previo
                                  </p>
                                  <pre className="mt-1 whitespace-pre-wrap font-sans text-xs leading-5 text-foreground/85">
                                    {item.history}
                                  </pre>
                                </div>
                              ) : null}

                              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                                <div className="rounded-xl border border-border bg-card p-3.5">
                                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                    Respuesta generada
                                  </p>
                                  <p className="mt-1.5 whitespace-pre-wrap font-editorial text-sm leading-6 text-foreground">
                                    {item.generated_answer}
                                  </p>
                                </div>
                                <div className="rounded-xl border border-border bg-card p-3.5">
                                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                    Referencia oficial DIGEMID
                                  </p>
                                  <p className="mt-1.5 whitespace-pre-wrap font-editorial text-sm leading-6 text-foreground/90">
                                    {item.reference_answer || "(Caso fuera de dominio: se espera rechazo explícito)"}
                                  </p>
                                </div>
                              </div>

                              {item.claims.length > 0 ? (
                                <div className="space-y-2">
                                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                    Afirmaciones auditadas por el juez ({item.claims.filter((c) => c.supported).length}/{item.claims.length} respaldadas)
                                  </p>
                                  <ul className="space-y-1.5">
                                    {item.claims.map((claim, index) => (
                                      <li
                                        className="flex items-start gap-2.5 rounded-lg border border-border bg-card px-3 py-2 text-xs"
                                        key={`${item.case_id}-claim-${index}`}
                                      >
                                        {claim.supported ? (
                                          <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-emerald-700 dark:text-emerald-400" aria-hidden="true" />
                                        ) : (
                                          <XCircleIcon className="mt-0.5 size-4 shrink-0 text-rose-700 dark:text-rose-400" aria-hidden="true" />
                                        )}
                                        <div className="min-w-0 flex-1">
                                          <p className="font-medium text-foreground">{claim.claim}</p>
                                          <p className="mt-0.5 text-[11px] text-muted-foreground">{claim.reason}</p>
                                        </div>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}

                              {item.retrieved_contexts.length > 0 ? (
                                <div className="space-y-1.5">
                                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                    Contextos recuperados ({item.retrieved_contexts.length})
                                  </p>
                                  <div className="flex flex-wrap gap-2">
                                    {item.retrieved_contexts.map((ctx, idx) => (
                                      <span
                                        className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-[11px] text-foreground"
                                        key={`${item.case_id}-ctx-${idx}`}
                                      >
                                        <FileTextIcon className="size-3 text-muted-foreground" aria-hidden="true" />
                                        {ctx.filename}
                                        {ctx.page != null ? ` · p. ${ctx.page}` : ""}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  description,
  current,
  previous,
}: {
  label: string;
  description: string;
  current: number | null | undefined;
  previous: number | null | undefined;
}) {
  const delta =
    current != null && previous != null ? Math.round((current - previous) * 100) : null;
  const pct = current != null ? Math.max(0, Math.min(100, Math.round(current * 100))) : 0;

  return (
    <div className="flex flex-col justify-between rounded-2xl border border-border bg-card p-4">
      <div>
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {label}
          </p>
          {delta !== null && delta !== 0 ? (
            <span
              className={cn(
                "rounded px-1.5 py-0.5 font-mono text-[11px] font-medium",
                delta > 0
                  ? "bg-emerald-700/12 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-300"
                  : "bg-rose-700/12 text-rose-800 dark:bg-rose-400/15 dark:text-rose-300",
              )}
            >
              {delta > 0 ? `+${delta}%` : `${delta}%`}
            </span>
          ) : null}
        </div>
        <p className={cn("mt-2 font-editorial text-3xl font-semibold", scoreTextTone(current))}>
          {formatPercent(current)}
        </p>
        <p className="mt-1 text-[11px] leading-4 text-muted-foreground">{description}</p>
      </div>
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-background">
        <div
          className={cn("h-full rounded-full transition-all duration-300", scoreTone(current))}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function OperationalStat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="truncate text-[11px] text-muted-foreground">{label}</p>
        <p className="font-mono text-sm font-semibold text-foreground">{value}</p>
      </div>
    </div>
  );
}

function ScorePill({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-0.5 text-[11px]">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-semibold", scoreTextTone(value))}>
        {formatPercent(value)}
      </span>
    </span>
  );
}
