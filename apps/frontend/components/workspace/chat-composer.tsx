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
        "relative z-20 shrink-0 border-t border-border bg-card/60 px-5 pt-4 pb-[calc(0.85rem+env(safe-area-inset-bottom))] md:px-8 md:pb-4",
        className,
      )}
    >
      <div className="mx-auto w-full max-w-4xl">
        <div className="w-full">
          <PromptInput
            className="relative border border-border bg-popover shadow-[0_14px_38px_-28px_rgba(19,36,51,0.38)] transition-[box-shadow,border-color] duration-200 ease-out focus-within:border-brand-accent/60 focus-within:ring-brand-accent/20"
            onSubmit={(message, event) => {
              event.preventDefault();
              submitQuestion(message.text);
            }}
          >
            <PromptInputTextarea
              className="min-h-15 resize-none bg-transparent px-5 py-[1.15rem] pr-16 text-sm leading-6 text-foreground shadow-none placeholder:text-muted-foreground/80 focus-visible:ring-0"
              disabled={isLoading}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Pregunte sobre normativa, registros o farmacovigilancia..."
              rows={1}
              value={input}
            />
            <PromptInputSubmit
              aria-label={isLoading ? "Detener respuesta" : "Enviar consulta"}
              className="absolute right-2.5 bottom-2.5 size-10 rounded-lg bg-brand-accent text-brand-accent-foreground shadow-sm transition-[background-color,transform] duration-150 ease-out hover:scale-[1.02] hover:bg-brand-accent/90 active:scale-[0.97]"
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
