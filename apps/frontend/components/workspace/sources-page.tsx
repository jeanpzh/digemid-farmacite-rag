"use client";

import { ChevronLeftIcon, ChevronRightIcon, FileUpIcon, SearchIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress, ProgressLabel, ProgressValue } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SourceDetails } from "@/components/workspace/source-details";
import { useIsMobile } from "@/hooks/use-mobile";
import {
  chatStatus, defaultCorpusUrl, indexLabels, isAvailable, isProcessing, libraryPath,
  libraryRequest, sourceOrigin, sourcesSchema, uploadSchema, type LibrarySource,
} from "@/lib/source-library";
import { cn } from "@/lib/utils";

const pageSize = 10;
const metrics = [
  { value: "available", label: "Disponible en chat", tone: "bg-emerald-600", matches: isAvailable },
  { value: "processing", label: "En proceso", tone: "bg-amber-500", matches: isProcessing },
  { value: "attention", label: "Requiere atención", tone: "bg-red-600", matches: (source: LibrarySource) => source.status === "failed" || chatStatus(source) === "En revisión" },
] as const;
const origins = [
  { value: "all", label: "Todos los orígenes" },
  { value: "corpus", label: "Venta sin receta" },
  { value: "upload", label: "Añadidos" },
];

function Status({ label, tone }: { label: string; tone: string }) {
  return <span className="inline-flex items-center gap-2"><span aria-hidden="true" className={cn("size-2 shrink-0 rounded-full", tone)} />{label}</span>;
}

const indexTone = {
  pending: "bg-muted-foreground",
  processing: "bg-amber-500",
  indexed: "bg-emerald-600",
  failed: "bg-red-600",
};

export function SourcesPage() {
  const [documents, setDocuments] = useState<LibrarySource[] | null>(null);
  const [loadError, setLoadError] = useState("");
  const [notice, setNotice] = useState("");
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const [batchIds, setBatchIds] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [query, setQuery] = useState("");
  const [origin, setOrigin] = useState("all");
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const requestVersion = useRef(0);
  const uploading = useRef(false);
  const mobile = useIsMobile();

  const refresh = useCallback(async () => {
    const version = ++requestVersion.current;
    try {
      const response = await libraryRequest(libraryPath);
      const result = sourcesSchema.parse(await response.json());
      if (version !== requestVersion.current) return;
      setDocuments(result.documents);
      setLoadError("");
    } catch (error) {
      if (version === requestVersion.current) {
        setLoadError(error instanceof Error ? error.message : "No se pudieron cargar las fuentes.");
      }
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  const waiting = documents?.some(isProcessing) ?? false;
  useEffect(() => {
    if (!waiting && !isUploading) return;
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(timer);
  }, [isUploading, refresh, waiting]);

  async function upload(files: FileList) {
    if (uploading.current || !files.length) return;
    uploading.current = true;
    setIsUploading(true);
    setNotice("");
    setUploadErrors([]);
    setBatchIds([]);

    try {
      for (const file of Array.from(files)) {
        try {
          if (!/\.pdf$/i.test(file.name)) throw new Error("Selecciona un archivo PDF.");
          const params = new URLSearchParams({ filename: file.name });
          const response = await libraryRequest(`${libraryPath}/uploads?${params}`, {
            method: "POST",
            headers: { "Content-Type": "application/pdf" },
            body: file,
          });
          const { document, duplicate } = uploadSchema.parse(await response.json());
          if (duplicate) {
            setNotice((current) => `${current}${current ? " · " : ""}Ya existe: ${file.name}`);
          } else {
            setBatchIds((current) => [...current, document.id]);
            setFilter("");
            setOrigin("all");
            setQuery("");
            setPage(0);
          }
        } catch (error) {
          setUploadErrors((current) => [...current, `${file.name} · ${error instanceof Error ? error.message : "No se pudo subir."}`]);
        }
      }
    } finally {
      uploading.current = false;
      setIsUploading(false);
      await refresh();
    }
  }

  const sources = documents ?? [];
  const selected = sources.find((source) => source.id === selectedId);
  const batch = sources.filter((source) => batchIds.includes(source.id));
  const finished = batch.filter((source) => !isProcessing(source)).length;
  const processing = batch.filter((source) => source.status === "processing").length;
  const pending = batch.filter((source) => source.status === "pending").length;
  const failed = batch.filter((source) => source.status === "failed").length;
  const selectedFilter = metrics.find((item) => item.value === filter);
  const filtered = sources.filter((source) =>
    (!selectedFilter || selectedFilter.matches(source)) &&
    (origin === "all" || source.origin === origin) &&
    source.filename.toLocaleLowerCase("es").includes(query.trim().toLocaleLowerCase("es")),
  );
  const currentPage = Math.min(page, Math.max(0, Math.ceil(filtered.length / pageSize) - 1));
  const start = currentPage * pageSize;

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col overflow-hidden bg-background">
      <header className="flex h-15 shrink-0 items-center border-b bg-card/65 px-5 text-sm font-semibold md:px-7">Fuentes</header>
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <div className="mx-auto flex max-w-5xl flex-col gap-4">
            <div className="mb-2">
              <h1 className="font-editorial text-3xl font-semibold tracking-tight md:text-4xl">Fuentes</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Corpus predeterminado · <a className="underline-offset-4 hover:underline" href={defaultCorpusUrl} target="_blank" rel="noreferrer">DIGEMID · Venta sin receta</a>
              </p>
            </div>
            {loadError && (
              <Alert variant="destructive" className="flex flex-wrap items-center justify-between gap-2">
                <AlertDescription>{loadError}</AlertDescription>
                <Button onClick={() => void refresh()} variant="outline">Reintentar</Button>
              </Alert>
            )}
            {documents && (
              <>
                <Card className="grid grid-cols-1 gap-0 py-0 sm:grid-cols-3">
                  {metrics.map(({ value, label, tone, matches }) => (
                    <Button
                      aria-pressed={filter === value}
                      className="h-auto min-h-16 flex-col items-start gap-1 rounded-none border-b border-border px-4 py-3 last:border-b-0 sm:border-r sm:border-b-0 sm:last:border-r-0"
                      key={value}
                      onClick={() => { setFilter(filter === value ? "" : value); setPage(0); }}
                      variant={filter === value ? "secondary" : "ghost"}
                    >
                      <span className="font-editorial text-2xl leading-none">{documents.filter(matches).length}</span>
                      <span className="text-xs"><Status label={label} tone={tone} /></span>
                    </Button>
                  ))}
                </Card>

                <Card
                  className={cn("flex-row flex-wrap items-center justify-between gap-3 border border-dashed bg-transparent px-4 py-4 ring-0", dragging && "border-ring bg-accent")}
                  onDragOver={(event) => { if (!event.dataTransfer.types.includes("Files")) return; event.preventDefault(); setDragging(true); }}
                  onDragLeave={(event) => { if (!(event.relatedTarget instanceof Node) || !event.currentTarget.contains(event.relatedTarget)) setDragging(false); }}
                  onDrop={(event) => { event.preventDefault(); setDragging(false); void upload(event.dataTransfer.files); }}
                >
                  <div>
                    <h2 className="text-sm font-semibold">Arrastra tus PDF aquí</h2>
                    <p className="mt-1 text-xs text-muted-foreground">Solo se indexan los archivos nuevos.</p>
                  </div>
                  <input
                    accept="application/pdf,.pdf" hidden multiple
                    onChange={(event) => { if (event.currentTarget.files) void upload(event.currentTarget.files); event.currentTarget.value = ""; }}
                    ref={fileInput} type="file"
                  />
                  <Button disabled={isUploading} onClick={() => fileInput.current?.click()} variant="outline">
                    <FileUpIcon aria-hidden="true" /> {isUploading ? "Subiendo…" : "Elegir PDF"}
                  </Button>
                </Card>

                {notice && <p className="text-sm text-muted-foreground" role="status">{notice}</p>}
                {uploadErrors.length > 0 && <Alert variant="destructive"><AlertDescription><ul>{uploadErrors.map((error, index) => <li key={index}>{error}</li>)}</ul></AlertDescription></Alert>}
                {batchIds.length > 0 && (
                  <Card className="gap-1 px-4 py-3">
                    <Progress className="[&_[data-slot=progress-track]]:h-2 [&_[data-slot=progress-track]]:bg-secondary" value={finished} max={batchIds.length}>
                      <ProgressLabel>Lote actual</ProgressLabel>
                      <ProgressValue>{() => `${finished} de ${batchIds.length} procesados`}</ProgressValue>
                    </Progress>
                    <p className="text-xs text-muted-foreground" role="status">
                      {[processing ? `${processing} indexando` : "", pending ? `${pending} en cola` : "", failed ? `${failed} con error` : "", isUploading ? "Subiendo archivos" : ""].filter(Boolean).join(" · ")}
                    </p>
                  </Card>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative min-w-36 flex-1">
                    <SearchIcon aria-hidden="true" className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
                    <Input aria-label="Buscar documento o norma" className="h-9 border-border pl-8" placeholder="Buscar documento o norma" value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); }} />
                  </div>
                  <Select items={origins} value={origin} onValueChange={(value) => { setOrigin(value ?? "all"); setPage(0); }}>
                    <SelectTrigger aria-label="Origen" className="h-9 border-border"><SelectValue /></SelectTrigger>
                    <SelectContent>{origins.map(({ value, label }) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent>
                  </Select>
                  {filter && <Button onClick={() => { setFilter(""); setPage(0); }} variant="ghost">Ver todos</Button>}
                </div>
                <Card className="gap-0 py-0">
                  <Table aria-label="Estado de los documentos">
                    <TableHeader className="bg-card">
                      <TableRow>
                        <TableHead className="px-3">Documento</TableHead>
                        <TableHead>Indexación</TableHead>
                        <TableHead className="hidden sm:table-cell">En chat</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filtered.slice(start, start + pageSize).map((source) => (
                        <TableRow className="cursor-pointer data-[state=selected]:bg-accent" key={source.id} data-state={selectedId === source.id ? "selected" : undefined} onClick={() => setSelectedId(source.id)}>
                          <TableCell className="px-3 whitespace-normal">
                            <button type="button" className="wrap-anywhere text-left font-medium hover:underline focus-visible:underline" aria-expanded={selectedId === source.id} onClick={() => setSelectedId(source.id)}>{source.filename}</button>
                            <p className="text-xs text-muted-foreground">{sourceOrigin(source)}</p>
                          </TableCell>
                          <TableCell className="text-xs sm:text-sm">
                            <Status label={indexLabels[source.status]} tone={indexTone[source.status]} />
                            <p className="mt-1 text-xs text-muted-foreground sm:hidden">{chatStatus(source)}</p>
                          </TableCell>
                          <TableCell className="hidden sm:table-cell"><Status label={chatStatus(source)} tone={isAvailable(source) ? "bg-emerald-600" : source.status === "indexed" && source.publication === "review" ? "bg-amber-500" : "bg-muted-foreground"} /></TableCell>
                        </TableRow>
                      ))}
                      {!filtered.length && <TableRow><TableCell colSpan={3} className="p-5 text-center text-sm text-muted-foreground">No hay documentos para mostrar.</TableCell></TableRow>}
                    </TableBody>
                  </Table>
                  {filtered.length > 0 && (
                    <div className="flex items-center justify-between border-t px-3 py-2 text-xs text-muted-foreground">
                      <span>{start + 1}–{Math.min(start + pageSize, filtered.length)} de {filtered.length}</span>
                      <div className="flex gap-1">
                        <Button aria-label="Página anterior" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)} size="icon-xs" variant="ghost"><ChevronLeftIcon /></Button>
                        <Button aria-label="Página siguiente" disabled={start + pageSize >= filtered.length} onClick={() => setPage(currentPage + 1)} size="icon-xs" variant="ghost"><ChevronRightIcon /></Button>
                      </div>
                    </div>
                  )}
                </Card>
              </>
            )}
            {!documents && !loadError && <p className="text-sm text-muted-foreground" role="status">Cargando fuentes…</p>}
          </div>
        </div>
        {selected && !mobile && (
          <aside aria-label="Ficha del documento" className="hidden w-[min(34%,25rem)] min-w-72 shrink-0 flex-col border-l bg-background md:flex">
            <div className="flex items-start justify-between gap-3 p-5">
              <h2 className="wrap-anywhere font-editorial text-2xl leading-tight font-semibold">{selected.filename}</h2>
              <Button aria-label="Cerrar detalles" onClick={() => setSelectedId("")} size="icon-sm" variant="ghost"><XIcon /></Button>
            </div>
            <SourceDetails key={selected.id} source={selected} documents={sources} refresh={refresh} />
          </aside>
        )}
        {selected && mobile && (
          <Sheet open onOpenChange={(open) => { if (!open) setSelectedId(""); }}>
            <SheetContent className="w-[min(100%,25rem)]">
              <SheetHeader className="pr-11"><SheetTitle className="wrap-anywhere font-editorial text-xl">{selected.filename}</SheetTitle></SheetHeader>
              <SourceDetails key={selected.id} source={selected} documents={sources} refresh={refresh} />
            </SheetContent>
          </Sheet>
        )}
      </div>
    </div>
  );
}
