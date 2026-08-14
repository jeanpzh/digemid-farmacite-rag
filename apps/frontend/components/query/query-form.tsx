"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";

import {
  PromptInput,
  PromptInputFooter,
  type PromptInputMessage,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";
import { useQueryContext } from "@/components/query/query-provider";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  queryRequestSchema,
  type QueryRequest,
} from "@/lib/validation/query";

export function QueryForm() {
  const {
    actions: { setHasDraft, stop, submitQuestion },
    meta: { isPending, maxQuestionLength },
    state: { status },
  } = useQueryContext();
  const form = useForm<QueryRequest>({
    defaultValues: { question: "" },
    resolver: zodResolver(queryRequestSchema),
  });
  const question = useWatch({ control: form.control, name: "question" }) ?? "";
  const questionError = form.formState.errors.question;

  function onSubmit({ text }: PromptInputMessage) {
    const parsed = queryRequestSchema.safeParse({ question: text });
    if (!parsed.success) {
      form.setError("question", {
        message: parsed.error.issues[0]?.message,
      });
      return;
    }

    form.clearErrors("question");
    submitQuestion(parsed.data.question);
    form.reset();
    setHasDraft(false);
  }

  return (
    <FieldGroup>
      <Field data-invalid={questionError ? "true" : undefined}>
        <PromptInput onSubmit={onSubmit} className="mt-4 w-full max-w-2xl mx-auto relative">
          <PromptInputTextarea
            aria-describedby="query-help query-count query-error"
            aria-invalid={questionError ? "true" : "false"}
            id="question"
            maxLength={maxQuestionLength}
            onChange={(event) => {
              const value = event.currentTarget.value;
              form.setValue("question", value);
              setHasDraft(Boolean(value.trim()));
            }}
            placeholder="¿Qué desea conocer sobre un medicamento o registro sanitario?"
            value={question}
          />
          <PromptInputFooter>
            <FieldDescription className="text-xs" id="query-help">
              <span aria-live="polite" className="block" id="query-count">
                {question.length.toLocaleString("es-PE")} / {maxQuestionLength}
              </span>
            </FieldDescription>
            <PromptInputSubmit
              aria-label="Enviar consulta"
              disabled={isPending || !question.trim()}
              onStop={stop}
              status={status}
            />
          </PromptInputFooter>
        </PromptInput>
        <FieldError errors={[questionError]} id="query-error" />
      </Field>
    </FieldGroup>
  );
}
