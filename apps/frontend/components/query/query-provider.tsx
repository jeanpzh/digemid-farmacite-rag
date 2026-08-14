"use client";

import { createContext, use, useState, type ReactNode } from "react";

import {
  useQueryController,
  type QueryControllerState,
} from "@/hooks/use-query-controller";
import { MAX_QUESTION_LENGTH } from "@/lib/validation/query";

type QueryContextValue = {
  state: QueryControllerState;
  actions: {
    submitQuestion: (question: string) => void;
    setHasDraft: (hasDraft: boolean) => void;
    stop: () => void;
  };
  meta: {
    hasDraft: boolean;
    isPending: boolean;
    maxQuestionLength: number;
  };
};

const QueryContext = createContext<QueryContextValue | null>(null);

export function QueryProvider({ children }: { children: ReactNode }) {
  const { state, isPending, submitQuestion, stop } = useQueryController();
  const [hasDraft, setHasDraft] = useState(false);
  const value: QueryContextValue = {
    state,
    actions: { submitQuestion, setHasDraft, stop },
    meta: { hasDraft, isPending, maxQuestionLength: MAX_QUESTION_LENGTH },
  };

  return <QueryContext value={value}>{children}</QueryContext>;
}

export function useQueryContext() {
  const context = use(QueryContext);
  if (!context) {
    throw new Error("useQueryContext must be used within QueryProvider");
  }
  return context;
}
