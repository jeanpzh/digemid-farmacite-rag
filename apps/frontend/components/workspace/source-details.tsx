"use client";

import { CheckCircle2Icon, CircleIcon, LoaderCircleIcon } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getDocumentPdfUrl } from "@/lib/document-url";
import {
  chatStatus, indexLabels, isAvailable, isProcessing, libraryPath, libraryRequest,
  sourceOrigin, type LibrarySource,
} from "@/lib/source-library";

const formatDate = new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short" });

export function SourceStatuses({ source }: { source: LibrarySource }) {
  return (
    <div className="flex flex-wrap gap-2">
      <Badge variant={source.status === "failed" ? "destructive" : "outline"}>{indexLabels[source.status]}</Badge>
      <Badge variant={isAvailable(source) ? "secondary" : "outline"}>{chatStatus(source)}</Badge>
    </div>
  );
}

export function SourceDetails({
  source,
  documents,
  refresh,
}: {
  source: LibrarySource;
  documents: LibrarySource[];
  refresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [replaces, setReplaces] = useState("none");
  const canPublish = source.status === "indexed" && source.publication === "review";
  const previous = documents.find((item) => item.id === source.replaces_id);
  const replacement = documents.find((item) => item.replaces_id === source.id);
  const available = documents.filter(isAvailable);
  const versionChoices = [{ value: "none", label: "Publicar como fuente nueva" }, ...available.map(
    (item) => ({ value: item.id, label: item.filename }),
  )];

  async function action(suffix: "retry" | "publish", data?: object) {
    setBusy(true);
    setError("");
    try {
      await libraryRequest(`${libraryPath}/${source.id}/${suffix}`, {
        method: "POST",
        ...(data && { headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
      });
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo completar la operación.");
    } finally {
      setBusy(false);
    }
  }

  function publish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    void action("publish", {
      replaces_id: replaces === "none" ? null : replaces,
      source_url: String(values.get("sourceUrl") ?? "").trim() || null,
      effective_on: values.get("effectiveOn") || null,
    });
  }

  const pdf = getDocumentPdfUrl(source.id, source.version);
  const officialUrl = source.source_url && /^https?:\/\//i.test(source.source_url) ? source.source_url : null;
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-5 pb-6">
      <SourceStatuses source={source} />
      <Tabs className="gap-5" defaultValue={source.status === "indexed" ? "details" : "activity"}>
        <TabsList aria-label="Ficha del documento" className="w-full border border-border">
          <TabsTrigger value="details">Detalles</TabsTrigger>
          <TabsTrigger value="versions">Versiones</TabsTrigger>
          <TabsTrigger value="activity">Actividad</TabsTrigger>
        </TabsList>
        <TabsContent value="details">
          <dl className="grid grid-cols-2 gap-y-3 text-sm">
            <dt className="text-muted-foreground">Origen</dt><dd>{sourceOrigin(source)}</dd>
            <dt className="text-muted-foreground">Añadido</dt><dd>{formatDate.format(new Date(source.created_at))}</dd>
            <dt className="text-muted-foreground">Vigencia</dt><dd>{source.effective_on ?? "Por verificar"}</dd>
            {source.indexed_at && <><dt className="text-muted-foreground">Indexado</dt><dd>{formatDate.format(new Date(source.indexed_at))}</dd></>}
          </dl>
          <div className="mt-5 flex flex-wrap gap-3">
            {pdf && <a href={pdf} target="_blank" rel="noreferrer" className="underline underline-offset-4">Abrir PDF</a>}
            {officialUrl && <a href={officialUrl} target="_blank" rel="noreferrer" className="underline underline-offset-4">Ver fuente oficial</a>}
          </div>
        </TabsContent>
        <TabsContent value="versions">
          {previous && <p className="mb-3 text-sm">Reemplazó a <strong>{previous.filename}</strong>.</p>}
          {replacement && <p className="mb-3 text-sm">Reemplazado por <strong>{replacement.filename}</strong>.</p>}
          {canPublish ? (
            <form className="flex flex-col gap-3" onSubmit={publish}>
              <h3 className="font-editorial text-lg font-semibold">Publicar en chat</h3>
              <label className="grid gap-1 text-sm">Enlace a la fuente oficial
                <Input name="sourceUrl" defaultValue={officialUrl ?? ""} placeholder="https://" type="url" />
              </label>
              <label className="grid gap-1 text-sm">Fecha de vigencia verificada
                <Input name="effectiveOn" defaultValue={source.effective_on ?? ""} type="date" />
              </label>
              <Select items={versionChoices} value={replaces} onValueChange={(value) => setReplaces(value ?? "none")}>
                <SelectTrigger aria-label="Fuente que se reemplazará" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>{versionChoices.map(({ value, label }) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent>
              </Select>
              {replaces !== "none" && <p className="text-sm text-muted-foreground">La versión actual seguirá disponible hasta que apruebes el reemplazo.</p>}
              <Button type="submit" disabled={busy}>{replaces === "none" ? "Publicar en chat" : "Aprobar reemplazo"}</Button>
            </form>
          ) : !previous && !replacement ? <p className="text-sm text-muted-foreground">No hay reemplazos registrados.</p> : null}
        </TabsContent>
        <TabsContent value="activity">
          <h3 className="mb-4 font-editorial text-xl font-semibold">Progreso de indexación</h3>
          <ol className="space-y-4 text-sm">
            <li className="flex items-center gap-2"><CheckCircle2Icon aria-hidden="true" className="size-4 text-emerald-700 dark:text-emerald-400" />PDF recibido</li>
            {source.chunks_total !== null && <li className="flex items-center gap-2"><CheckCircle2Icon aria-hidden="true" className="size-4 text-emerald-700 dark:text-emerald-400" />Texto extraído</li>}
            <li className="flex items-center gap-2">
              {source.status === "processing" ? <LoaderCircleIcon aria-hidden="true" className="size-4 motion-safe:animate-spin" /> : <CircleIcon aria-hidden="true" className="size-4" />}
              {source.index_stage === "embedding" && source.status === "processing" ? "Preparando fragmentos"
                : source.index_stage === "saving" && source.status === "processing" ? "Guardando fragmentos"
                : source.index_stage === "extracting" && source.status === "processing" ? "Extrayendo texto"
                : source.status === "indexed" ? "Indexación completada" : indexLabels[source.status]}
            </li>
          </ol>
          {source.chunks_total !== null && source.chunks_done !== null && source.status !== "failed" && (
            <div className="mt-4">
              <Progress aria-label="Fragmentos preparados" className="[&_[data-slot=progress-track]]:h-2 [&_[data-slot=progress-track]]:bg-secondary" value={source.chunks_done} max={source.chunks_total} />
              <p className="mt-1 text-sm text-muted-foreground">{source.chunks_done} de {source.chunks_total} fragmentos {source.status === "indexed" ? "guardados" : "preparados"}</p>
            </div>
          )}
          {source.status === "failed" && (
            <div className="mt-4 space-y-3">
              <p className="text-sm text-destructive">{source.error}</p>
              <Button disabled={busy} onClick={() => void action("retry")} variant="outline">Reintentar</Button>
            </div>
          )}
          {!isAvailable(source) && source.publication === "review" && (
            <p className="mt-5 border-t pt-4 text-sm text-muted-foreground">
              {isProcessing(source) ? "Disponible tras indexación y revisión." : "Disponible tras aprobación."}
            </p>
          )}
        </TabsContent>
      </Tabs>
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
    </div>
  );
}
