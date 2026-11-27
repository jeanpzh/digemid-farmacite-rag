import { z } from "zod";

export const claimVerdictSchema = z.object({
  claim: z.string(),
  supported: z.boolean(),
  reason: z.string(),
});

export const retrievedContextSchema = z.object({
  filename: z.string(),
  page: z.number().nullable().optional(),
  snippet: z.string(),
});

export const evalRunSchema = z.object({
  id: z.number(),
  name: z.string(),
  git_sha: z.string().nullable().optional(),
  dataset_name: z.string(),
  chat_provider: z.string(),
  chat_model: z.string(),
  router_model: z.string(),
  embedding_model: z.string(),
  judge_model: z.string(),
  sample_count: z.number(),
  avg_faithfulness: z.number().nullable().optional(),
  avg_context_precision: z.number().nullable().optional(),
  avg_context_recall: z.number().nullable().optional(),
  avg_response_relevancy: z.number().nullable().optional(),
  avg_retrieval_ms: z.number().nullable().optional(),
  p95_retrieval_ms: z.number().nullable().optional(),
  avg_ttft_ms: z.number().nullable().optional(),
  refusal_accuracy: z.number().nullable().optional(),
  created_at: z.string().nullable().optional(),
});

export const evalResultSchema = z.object({
  id: z.number(),
  run_id: z.number(),
  case_id: z.string(),
  category: z.enum(["standalone", "followup", "multi_medicine", "out_of_domain"]),
  question: z.string(),
  history: z.string(),
  reference_answer: z.string(),
  generated_answer: z.string(),
  retrieved_contexts: z.array(retrievedContextSchema).default([]),
  faithfulness: z.number().nullable().optional(),
  context_precision: z.number().nullable().optional(),
  context_recall: z.number().nullable().optional(),
  response_relevancy: z.number().nullable().optional(),
  retrieval_ms: z.number().nullable().optional(),
  ttft_ms: z.number().nullable().optional(),
  passed_refusal: z.boolean().nullable().optional(),
  claims: z.array(claimVerdictSchema).default([]),
  created_at: z.string().nullable().optional(),
});

export const evalRunsResponseSchema = z.object({
  runs: z.array(evalRunSchema),
});

export const evalRunDetailResponseSchema = z.object({
  run: evalRunSchema,
  results: z.array(evalResultSchema),
});

export const turnEvaluationSchema = z.object({
  faithfulness: z.number().nullable().optional(),
  response_relevancy: z.number().nullable().optional(),
  claims: z.array(claimVerdictSchema).default([]),
  judge_model: z.string().default(""),
});

export type ClaimVerdict = z.infer<typeof claimVerdictSchema>;
export type EvalRun = z.infer<typeof evalRunSchema>;
export type EvalResult = z.infer<typeof evalResultSchema>;
export type TurnEvaluation = z.infer<typeof turnEvaluationSchema>;

export type TurnEvalState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: TurnEvaluation };
