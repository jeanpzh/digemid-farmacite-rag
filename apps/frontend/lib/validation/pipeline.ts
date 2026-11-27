import { z } from "zod";

const pipelineModelSchema = z.object({ provider: z.string(), model: z.string() });

const retrievalSchema = z.object({
  max_distance: z.number(),
  min_results: z.number().int(),
  expansion_max_queries: z.number().int(),
});

export const pipelineSchema = z.object({
  answer: pipelineModelSchema,
  router: pipelineModelSchema,
  embeddings: pipelineModelSchema,
  judge: pipelineModelSchema,
  retrieval: retrievalSchema,
  trial_limits: retrievalSchema,
});

const metric = z.number().nullable();
const metricsSchema = z.object({
  avg_faithfulness: metric,
  avg_context_precision: metric,
  avg_context_recall: metric,
  avg_response_relevancy: metric,
  avg_retrieval_ms: metric,
  p95_retrieval_ms: metric,
  avg_ttft_ms: metric,
  refusal_accuracy: metric,
});

const resultSchema = z.object({
  type: z.literal("result"),
  dataset: z.string(),
  sample_count: z.number().int().positive(),
  baseline: metricsSchema,
  candidate: metricsSchema,
});

export const trialEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("progress"), completed: z.number(), total: z.number() }),
  z.object({ type: z.literal("error"), code: z.enum(["busy", "timeout", "failed"]) }),
  resultSchema,
]);

export type Pipeline = z.infer<typeof pipelineSchema>;
export type PipelineRetrieval = z.infer<typeof retrievalSchema>;
export type TrialResult = z.infer<typeof resultSchema>;
