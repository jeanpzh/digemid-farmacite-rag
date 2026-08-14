"use client";

import type { ComponentProps } from "react";

import {
  PromptInput,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { cn } from "@/lib/utils";

export function ChatComposer({ className }: ComponentProps<"div">) {
  const { input, isLoading, setInput, status, submitQuestion, stop } =
    useWorkspace();

  return (
    <div
      className={cn(
        "fixed right-0 bottom-0 z-20 w-auto border-t border-foreground/8 bg-background px-4 pt-4 pb-[calc(1rem+env(safe-area-inset-bottom))] transition-[left,right] duration-300 ease-out md:px-8 md:pt-5 md:pb-5",
        className,
      )}
    >
      <div className="mx-auto w-full max-w-3xl">
        <div className="w-full">
          <PromptInput
            className="relative bg-card transition-[box-shadow,transform] duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] focus-within:ring-brand-accent/50"
            onSubmit={(message, event) => {
              event.preventDefault();
              submitQuestion(message.text);
            }}
          >
            <PromptInputTextarea
              className="min-h-14 resize-none bg-transparent px-5 py-4 pr-14 text-sm leading-6 shadow-none focus-visible:ring-0"
              disabled={isLoading}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Pregunte sobre normativa, registros o farmacovigilancia..."
              rows={1}
              value={input}
            />
            <PromptInputSubmit
              aria-label={isLoading ? "Detener respuesta" : "Enviar consulta"}
              className="absolute right-2 bottom-2 size-10 rounded-xl bg-brand-accent text-brand-accent-foreground transition-transform duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] hover:scale-105 hover:bg-brand-accent/90"
              disabled={!input.trim() && !isLoading}
              onStop={stop}
              status={status}
            />
          </PromptInput>
          <p className="mt-2 text-center text-[11px] text-muted-foreground">
            Enter para enviar · Shift + Enter para una nueva línea
          </p>
        </div>
      </div>
    </div>
  );
}
