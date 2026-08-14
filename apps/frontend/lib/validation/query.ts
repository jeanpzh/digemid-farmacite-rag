import { z } from "zod";
import {
  citationLocationSchema,
  citationSchema,
  citationSourceSchema,
  ragDataPartSchemas,
  retrievalStatusSchema,
} from "@/lib/validation/rag-stream";
import type {
  Citation,
  RagDataParts,
  RetrievalStatus,
} from "@/lib/validation/rag-stream";

export const MAX_QUESTION_LENGTH = 4000;

export const questionSchema = z
  .string()
  .trim()
  .min(1, "Escriba una consulta antes de enviarla.")
  .max(
    MAX_QUESTION_LENGTH,
    `La consulta no puede superar los ${MAX_QUESTION_LENGTH} caracteres.`,
  );

export const queryRequestSchema = z.object({
  question: questionSchema,
});

export const queryErrorSchema = z.object({
  detail: z.string(),
});

export {
  citationLocationSchema,
  citationSchema,
  citationSourceSchema,
  retrievalStatusSchema,
};
export type { Citation, RetrievalStatus };
export type QueryRequest = z.infer<typeof queryRequestSchema>;
export type QueryStatus = RetrievalStatus;
export type QueryDataParts = RagDataParts;
export const queryDataPartSchemas = ragDataPartSchemas;
