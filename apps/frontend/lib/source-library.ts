import { z } from "zod";

export const sourceSchema = z.object({
  id: z.string(),
  version: z.string(),
  filename: z.string(),
  source_url: z.string().nullable(),
  origin: z.enum(["corpus", "upload"]),
  status: z.enum(["pending", "processing", "indexed", "failed"]),
  publication: z.enum(["published", "review", "archived"]),
  index_stage: z.enum(["extracting", "embedding", "saving", "complete"]).nullable(),
  chunks_total: z.number().nullable(),
  chunks_done: z.number().nullable(),
  error: z.string().nullable(),
  created_at: z.string(),
  indexed_at: z.string().nullable(),
  published_at: z.string().nullable(),
  updated_at: z.string(),
  replaces_id: z.string().nullable(),
  effective_on: z.string().nullable(),
});

export const sourcesSchema = z.object({ documents: z.array(sourceSchema) });
export const uploadSchema = z.object({ document: sourceSchema, duplicate: z.boolean() });

export type LibrarySource = z.infer<typeof sourceSchema>;

export const libraryPath = "/api/v1/source-library";
export const defaultCorpusUrl = "https://www.digemid.minsa.gob.pe/webDigemid/registro-sanitario/productos-farmaceuticos/venta-sin-receta/";
export const indexLabels = {
  pending: "En cola",
  processing: "Indexando…",
  indexed: "Indexado",
  failed: "Error",
};

export function isProcessing(source: LibrarySource) {
  return source.status === "pending" || source.status === "processing";
}

export function isAvailable(source: LibrarySource) {
  return source.status === "indexed" && source.publication === "published";
}

export function chatStatus(source: LibrarySource) {
  if (isAvailable(source)) return "Disponible";
  if (source.publication === "archived") return "Archivado";
  if (source.status === "indexed" && source.publication === "review") return "En revisión";
  return "No disponible";
}

export function sourceOrigin(source: LibrarySource) {
  return source.origin === "corpus" ? "Venta sin receta" : "Añadido";
}

export async function libraryRequest(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (response.ok) return response;

  if (response.status === 404) throw new Error("La biblioteca de fuentes no está habilitada.");
  if (response.status === 429) throw new Error("Espera un minuto antes de subir más archivos.");
  const data = await response.json().catch(() => null);
  throw new Error(typeof data?.detail === "string" ? data.detail : "No se pudo completar la operación.");
}
