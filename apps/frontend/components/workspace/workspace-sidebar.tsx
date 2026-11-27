"use client";

import { BarChart3Icon, FilesIcon, MessageSquareTextIcon, PlusIcon, SettingsIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { BrandLogo } from "@/components/brand-logo";
import { ThemeToggle } from "@/components/theme-toggle";
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
import { cn } from "@/lib/utils";

const workspaceLinks = [
  { href: "/chat", label: "Consultas", icon: MessageSquareTextIcon },
  { href: "/sources", label: "Fuentes", icon: FilesIcon },
  { href: "/evals", label: "Evaluaciones RAGAS", icon: BarChart3Icon },
  { href: "/settings", label: "Configuración", icon: SettingsIcon },
] as const;

export function WorkspaceSidebar() {
  const { startNewConversation } = useWorkspace();
  const pathname = usePathname();
  const router = useRouter();
  const [confirmNewConversation, setConfirmNewConversation] = useState(false);

  const isChat = pathname?.startsWith("/chat");

  function resetConversation() {
    startNewConversation();
    setConfirmNewConversation(false);
    if (!isChat) {
      router.push("/chat");
    }
  }

  return (
    <>
      <aside
        aria-label="Acciones de consulta"
        className="flex w-20 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground"
      >
        <div className="flex h-16 items-center justify-center border-b border-sidebar-border">
          <Link aria-label="Inicio DIGEMID" href="/chat">
            <BrandLogo aria-hidden="true" className="size-10 rounded-lg" />
          </Link>
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
          <div className="my-1 h-px w-8 bg-sidebar-border" />
          <nav aria-label="Navegación principal" className="flex flex-col items-center gap-2">
            {workspaceLinks.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href || pathname?.startsWith(`${href}/`);

              return (
                <Link
                  aria-current={isActive ? "page" : undefined}
                  aria-label={label}
                  className={cn(
                    "flex size-11 items-center justify-center rounded-xl transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sidebar-ring",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-foreground ring-1 ring-sidebar-border"
                      : "text-sidebar-foreground/65 hover:bg-sidebar-accent/70 hover:text-sidebar-foreground",
                  )}
                  href={href}
                  key={href}
                  title={label}
                >
                  <Icon className="size-5" aria-hidden="true" />
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex justify-center pb-5">
          <ThemeToggle />
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
