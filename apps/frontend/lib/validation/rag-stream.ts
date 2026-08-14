import type { UIDataPartSchemas } from "ai";
import { z } from "zod";

export const citationSourceSchema = z.object({
  documentId: z.string(),
  documentVersion: z.string(),
  chunkId: z.string(),
  filename: z.string(),
  url: z.url().nullable(),
});

export const citationLocationSchema = z.object({
  page: z.number().int(),
  pageLabel: z.string().nullable(),
  totalPages: z.number().int().nullable(),
  startIndex: z.number().int(),
  endIndex: z.number().int(),
});

export const citationSchema = z.object({
  id: z.string(),
  label: z.string().regex(/^S\d+$/),
  source: citationSourceSchema,
  location: citationLocationSchema,
  excerpt: z.string(),
});

export const retrievalStatusSchema = z.object({
  phase: z.literal("retrieval"),
  state: z.enum(["active", "complete", "error"]),
  label: z.string(),
});

export type Citation = z.infer<typeof citationSchema>;
export type RetrievalStatus = z.infer<typeof retrievalStatusSchema>;

export type RagDataParts = {
  status: RetrievalStatus;
  citation: Citation;
};

export const ragDataPartSchemas: UIDataPartSchemas = {
  "data-status": retrievalStatusSchema,
  "data-citation": citationSchema,
};
