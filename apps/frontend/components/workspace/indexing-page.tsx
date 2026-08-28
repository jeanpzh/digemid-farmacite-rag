"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  CircleDashedIcon,
  DownloadIcon,
  FileTextIcon,
  InfoIcon,
  PauseIcon,
  PlayIcon,
  RotateCcwIcon,
  XIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type RunStatus =
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";
type RunMode = "all" | "pending";
type ApiDocumentStatus = "pending" | "processing" | "indexed" | "failed";

type IndexingDocument = {
  id: number;
  filename: string;
  source_url: string | null;
  status: ApiDocumentStatus;
  stage: string;
  progress: number;
  last_error: string | null;
};

type IndexingRun = {
  run_id: string;
  collection: string;
  mode: RunMode;
  status: RunStatus;
  started_at: string;
  finished_at: string | null;
  completed: number;
  total: number;
  progress: number;
  stage: string;
  elapsed_seconds: number;
  documents: IndexingDocument[];
};

const indexingApi = "/api/v1/indexing";

const runCopy: Record<RunStatus | "idle", { label: string; stage: string }> = {
  idle: {
    label: "Listo para iniciar",
    stage: "Esperando una acción",
  },
  running: {
    label: "En curso",
    stage: "Generando embeddings",
  },
  paused: {
    label: "Pausado",
    stage: "En pausa",
  },
  completed: {
    label: "Completado",
    stage: "Indexación completa",
  },
  failed: {
    label: "Error",
    stage: "Error de indexación",
  },
  cancelled: {
    label: "Cancelado",
    stage: "Indexación cancelada",
  },
};

function documentStatus(status: ApiDocumentStatus) {
  switch (status) {
    case "indexed":
      return {
        label: "Indexado",
        icon: CheckCircle2Icon,
        className: "text-foreground",
      };
    case "processing":
      return {
        label: "En curso",
        icon: CircleDashedIcon,
        className: "text-muted-foreground",
      };
    case "failed":
      return {
        label: "Error",
        icon: AlertTriangleIcon,
        className: "text-foreground",
      };
    default:
      return {
        label: "En cola",
        icon: CircleDashedIcon,
        className: "text-muted-foreground",
      };
  }
}

function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}

function DocumentProgress({ value }: { value: number }) {
  const safeValue = Math.max(0, Math.min(100, value));

  return (
    <div className="flex min-w-[130px] items-center gap-3">
      <div
        aria-label={`${safeValue}% completado`}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={safeValue}
        className="h-1.5 flex-1 rounded-full bg-secondary"
        role="progressbar"
      >
        <div
          className="h-full rounded-full bg-[#726e62] transition-[width] duration-300"
          style={{ width: `${safeValue}%` }}
        />
      </div>
      <span className="w-10 text-right tabular-nums text-muted-foreground">
        {safeValue}%
      </span>
    </div>
  );
}

async function parseApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? "No se pudo actualizar la indexación.");
  }
  return response.json() as Promise<T>;
}

export function IndexingPage() {
  const [run, setRun] = useState<IndexingRun | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadLatest() {
      try {
        const response = await fetch(`${indexingApi}/runs/latest?collection=digemid`, {
          cache: "no-store",
          signal: controller.signal,
        });
        const latest = await parseApiResponse<IndexingRun | null>(response);
        setRun(latest);
      } catch (reason: unknown) {
        if (reason instanceof DOMException && reason.name === "AbortError") {
          return;
        }
        setError(reason instanceof Error ? reason.message : "No se pudo cargar la indexación.");
      } finally {
        setIsLoading(false);
      }
    }

    void loadLatest();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!run || (run.status !== "running" && run.status !== "paused")) {
      return;
    }

    const interval = window.setInterval(() => {
      fetch(`${indexingApi}/runs/${run.run_id}`, { cache: "no-store" })
        .then((response) => parseApiResponse<IndexingRun>(response))
        .then(setRun)
        .catch((reason: unknown) => {
          setError(reason instanceof Error ? reason.message : "No se pudo actualizar la indexación.");
        });
    }, 1500);

    return () => window.clearInterval(interval);
  }, [run]);

  const currentCopy = runCopy[run?.status ?? "idle"];
  const runMode = run?.mode ?? "pending";
  const documents = run?.documents ?? [];
  const canControlRun = run?.status === "running" || run?.status === "paused";
  const isBusy = pendingAction !== null;
  const tableMessage = isLoading
    ? "Cargando documentos..."
    : documents.length === 0
      ? "No hay documentos registrados todavía."
      : null;

  const collectionLabel = useMemo(
    () => (run?.collection ?? "digemid").toUpperCase(),
    [run?.collection],
  );

  async function startIndexing(mode: RunMode) {
    setPendingAction(`start-${mode}`);
    setError(null);
    try {
      const response = await fetch(`${indexingApi}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ collection: "digemid", mode }),
      });
      setRun(await parseApiResponse<IndexingRun>(response));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "No se pudo iniciar la indexación.");
    } finally {
      setPendingAction(null);
    }
  }

  async function controlRun(action: "pause" | "resume" | "cancel") {
    if (!run) return;

    setPendingAction(action);
    setError(null);
    try {
      const response = await fetch(`${indexingApi}/runs/${run.run_id}/${action}`, {
        method: "POST",
      });
      setRun(await parseApiResponse<IndexingRun>(response));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "No se pudo actualizar la indexación.");
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className="min-h-full overflow-y-auto bg-background text-foreground">
      <div className="mx-auto w-full max-w-[1600px] px-6 py-8 sm:px-10 sm:py-10 xl:px-12 xl:py-12">
        <header className="flex flex-col gap-8 border-b border-border/80 pb-9 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-5xl">
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-muted-foreground">
              Biblioteca local / Indexación
            </p>
            <h1 className="mt-4 font-editorial text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-foreground sm:text-6xl xl:text-[3rem]">
              Preparar la biblioteca documental
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">
              Descargue las fuentes oficiales y construya el índice local sin
              interrumpir las consultas.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row xl:pb-1">
            <Button
              className="h-12 justify-center rounded-md bg-[#12110e] px-5 text-[#f3f0e8] shadow-none hover:bg-[#3a3731] hover:text-[#f3f0e8]"
              disabled={isBusy || canControlRun}
              onClick={() => startIndexing("all")}
              type="button"
            >
              <DownloadIcon aria-hidden="true" />
              Descargar e indexar
            </Button>
            <Button
              className="h-12 justify-center rounded-md border-[#a9a393] bg-transparent px-5 text-foreground shadow-none hover:border-[#726e62] hover:bg-[#eee9dd] hover:text-foreground"
              disabled={isBusy || canControlRun}
              onClick={() => startIndexing("pending")}
              type="button"
              variant="outline"
            >
              Solo indexar pendientes
            </Button>
          </div>
        </header>

        {error ? (
          <div className="mt-5 flex items-start gap-3 rounded-md border border-destructive/40 bg-destructive/10 px-5 py-4 text-sm" role="alert">
            <AlertTriangleIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        <section
          aria-label="Estado de indexación"
          className="mt-8 rounded-md border border-border bg-card"
        >
          <div className="grid divide-y divide-border xl:grid-cols-[1.2fr_2.5fr_1.2fr_1.6fr_auto] xl:divide-x xl:divide-y-0">
            <div className="px-5 py-5 sm:px-7">
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Indexación {runMode === "pending" ? "de pendientes" : "inicial"}
              </p>
              <div className="mt-3 flex items-center gap-2 text-lg">
                <span
                  className={cn(
                    "size-2 rounded-full",
                    run?.status === "running" ? "bg-[#726e62]" : "bg-[#a9a393]",
                  )}
                />
                <span>{currentCopy.label}</span>
              </div>
            </div>

            <div className="px-5 py-5 sm:px-7">
              <div className="flex items-end justify-between gap-4">
                <span className="text-lg tabular-nums">
                  {run?.completed ?? 0} de {run?.total ?? 0} documentos
                </span>
                <span className="text-lg tabular-nums text-muted-foreground">
                  {run?.progress ?? 0}%
                </span>
              </div>
              <div
                aria-label={`${run?.progress ?? 0}% de la indexación completada`}
                aria-valuemax={100}
                aria-valuemin={0}
                aria-valuenow={run?.progress ?? 0}
                className="mt-4 h-2 rounded-full bg-secondary"
                role="progressbar"
              >
                <div
                  className="h-full rounded-full bg-[#726e62] transition-[width] duration-300"
                  style={{ width: `${run?.progress ?? 0}%` }}
                />
              </div>
            </div>

            <div className="px-5 py-5 sm:px-7">
              <p className="text-xs text-muted-foreground">Tiempo transcurrido</p>
              <p className="mt-3 text-lg tabular-nums">{run ? formatElapsed(run.elapsed_seconds) : "—"}</p>
            </div>

            <div className="px-5 py-5 sm:px-7">
              <p className="text-xs text-muted-foreground">Etapa actual</p>
              <p className="mt-3 text-lg">{run?.stage ?? currentCopy.stage}</p>
            </div>

            <div className="flex items-stretch divide-x divide-border">
              <Button
                aria-label={run?.status === "paused" ? "Reanudar indexación" : "Pausar indexación"}
                className="h-auto min-h-24 flex-col gap-2 rounded-none border-0 px-5 text-foreground hover:bg-muted hover:text-foreground"
                disabled={!canControlRun || isBusy}
                onClick={() => controlRun(run?.status === "paused" ? "resume" : "pause")}
                title={run?.status === "paused" ? "Reanudar" : "Pausar"}
                type="button"
                variant="ghost"
              >
                {run?.status === "paused" ? <PlayIcon aria-hidden="true" /> : <PauseIcon aria-hidden="true" />}
                <span className="text-xs font-normal">{run?.status === "paused" ? "Reanudar" : "Pausar"}</span>
              </Button>
              <Button
                aria-label="Cancelar indexación"
                className="h-auto min-h-24 flex-col gap-2 rounded-none border-0 px-5 text-foreground hover:bg-muted hover:text-foreground"
                disabled={!canControlRun || isBusy}
                onClick={() => controlRun("cancel")}
                title="Cancelar"
                type="button"
                variant="ghost"
              >
                <XIcon aria-hidden="true" />
                <span className="text-xs font-normal">Cancelar</span>
              </Button>
            </div>
          </div>
        </section>

        <section aria-labelledby="documents-heading" className="mt-6">
          <h2 className="sr-only" id="documents-heading">
            Documentos de la biblioteca
          </h2>
          <div className="overflow-hidden rounded-md border border-border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[930px] table-fixed border-collapse text-sm">
                <colgroup>
                  <col className="w-[24%]" />
                  <col className="w-[11%]" />
                  <col className="w-[27%]" />
                  <col className="w-[18%]" />
                  <col className="w-[20%]" />
                </colgroup>
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-[0.1em] text-muted-foreground">
                    <th className="px-5 py-5 font-medium sm:px-7">Documento</th>
                    <th className="px-5 py-5 font-medium">Origen</th>
                    <th className="px-5 py-5 font-medium">
                      <span className="inline-flex items-center gap-2">
                        Etapa
                        <InfoIcon aria-label="Etapas del proceso" className="size-4" />
                      </span>
                    </th>
                    <th className="px-5 py-5 font-medium">Progreso</th>
                    <th className="px-5 py-5 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {tableMessage ? (
                    <tr>
                      <td className="px-5 py-12 text-center text-muted-foreground sm:px-7" colSpan={5}>
                        {tableMessage}
                      </td>
                    </tr>
                  ) : documents.map((document) => {
                    const status = documentStatus(document.status);
                    const StatusIcon = status.icon;

                    return (
                      <tr className="border-b border-border last:border-b-0" key={document.id}>
                        <td className="px-5 py-4 sm:px-7">
                          <div className="flex min-w-0 items-center gap-4">
                            <FileTextIcon aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" />
                            <span className="min-w-0 truncate text-base text-foreground">{document.filename}</span>
                          </div>
                        </td>
                        <td className="px-5 py-4 text-muted-foreground">{collectionLabel}</td>
                        <td className="px-5 py-4 text-muted-foreground">
                          <span className="break-words" title={document.last_error ?? undefined}>
                            {document.stage}
                          </span>
                        </td>
                        <td className="px-5 py-4"><DocumentProgress value={document.progress} /></td>
                        <td className="px-5 py-4">
                          <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
                            <StatusIcon aria-hidden="true" className={cn("size-5", status.className)} />
                            <span className="whitespace-nowrap">{status.label}</span>
                            {document.status === "failed" ? (
                              <Button
                                aria-label={`Reintentar ${document.filename}`}
                                className="ml-auto h-8 rounded border-border px-3 text-xs text-foreground hover:bg-muted hover:text-foreground"
                                disabled={isBusy || canControlRun}
                                onClick={() => startIndexing("pending")}
                                type="button"
                                variant="outline"
                              >
                                <RotateCcwIcon aria-hidden="true" />
                                Reintentar pendientes
                              </Button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <footer className="mt-8 grid gap-8 pb-6 text-sm text-muted-foreground lg:grid-cols-[1fr_360px] lg:gap-12">
          <div className="flex items-start gap-3">
            <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-foreground" />
            <p>
              El proceso continúa en segundo plano. Puede volver a{" "}
              <Link className="underline underline-offset-4 hover:text-foreground" href="/chat">
                Consultas
              </Link>
              .
            </p>
          </div>
          <div className="border-l border-border pl-5">
            <p className="mb-3 text-xs uppercase tracking-[0.1em] text-muted-foreground">Estado del servicio</p>
            <p>La pantalla consulta el estado persistido cada 1,5 segundos mientras el proceso está activo.</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
