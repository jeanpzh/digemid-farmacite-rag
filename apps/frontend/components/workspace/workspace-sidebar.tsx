"use client";

import { PlusIcon } from "lucide-react";
import { Layers3Icon, Settings2Icon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { BrandLogo } from "@/components/brand-logo";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/workspace/workspace-provider";

export function WorkspaceSidebar() {
  const { startNewConversation } = useWorkspace();
  const pathname = usePathname();
  const [confirmNewConversation, setConfirmNewConversation] = useState(false);

  function resetConversation() {
    startNewConversation();
    setConfirmNewConversation(false);
  }

  return (
    <>
      <aside
        aria-label="Acciones de consulta"
        className="flex w-20 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground"
      >
        <div className="flex h-16 items-center justify-center border-b border-sidebar-border">
          <BrandLogo aria-hidden="true" className="size-10 rounded-lg" />
        </div>
        <div className="flex flex-1 flex-col items-center gap-3 px-3 py-5">
          <Button
            aria-label="Nueva conversación"
            className="size-11 rounded-xl bg-brand-accent text-brand-accent-foreground shadow-[0_10px_28px_-16px_rgba(142,137,123,0.9)] hover:bg-brand-accent/90 hover:text-brand-accent-foreground"
            onClick={() => setConfirmNewConversation(true)}
            title="Nueva conversación"
            type="button"
          >
            <PlusIcon aria-hidden="true" />
          </Button>
          <Link
            aria-label="Biblioteca e indexación"
            className={`inline-flex size-11 items-center justify-center rounded-xl border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent ${
              pathname === "/indexing"
                ? "border-border bg-secondary text-foreground"
                : "border-transparent text-sidebar-foreground/75 hover:border-sidebar-border hover:bg-sidebar-accent hover:text-sidebar-foreground"
            }`}
            href="/indexing"
            title="Biblioteca e indexación"
          >
            <Layers3Icon aria-hidden="true" />
          </Link>
        </div>
        <div className="flex justify-center pb-5">
          <Button
            aria-label="Ajustes"
            className="size-11 rounded-xl text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-foreground"
            title="Ajustes"
            type="button"
            variant="ghost"
          >
            <Settings2Icon aria-hidden="true" />
          </Button>
        </div>
      </aside>
      <Dialog open={confirmNewConversation} onOpenChange={setConfirmNewConversation}>
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>¿Iniciar una nueva conversación?</DialogTitle>
            <DialogDescription>
              Se borrará la conversación actual y sus fuentes consultadas.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setConfirmNewConversation(false)} variant="outline">
              Cancelar
            </Button>
            <Button
              className="bg-brand-accent text-brand-accent-foreground hover:bg-brand-accent/90"
              onClick={resetConversation}
            >
              Nueva conversación
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
