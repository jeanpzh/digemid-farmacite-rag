"use client";

import { MessageSquarePlusIcon } from "lucide-react";
import Link from "next/link";
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
import {
  Sidebar,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { cn } from "@/lib/utils";

export function WorkspaceSidebar() {
  const { startNewConversation } = useWorkspace();
  const [confirmNewConversation, setConfirmNewConversation] = useState(false);

  function resetConversation() {
    startNewConversation();
    setConfirmNewConversation(false);
  }

  return (
    <>
      <Sidebar collapsible="icon" className="border-sidebar-border/70">
        <SidebarHeader className="gap-4 p-4 group-data-[collapsible=icon]:p-2">
          <div className="group/header relative flex items-center justify-between gap-3 px-1 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:gap-0">
            <div className="flex min-w-0 items-center gap-3 group-data-[collapsible=icon]:size-8 group-data-[collapsible=icon]:justify-center">
              <BrandLogo
                aria-hidden="true"
                className="size-9 shrink-0 rounded-xl group-data-[collapsible=icon]:size-8 group-data-[collapsible=icon]:transition-opacity group-data-[collapsible=icon]:group-hover/header:opacity-0"
              />
              <p className="truncate text-md font-semibold tracking-[-0.02em] group-data-[collapsible=icon]:hidden">DIGEMID</p>
            </div>
            <div className="group-data-[collapsible=icon]:absolute group-data-[collapsible=icon]:left-1/2 group-data-[collapsible=icon]:-translate-x-1/2 group-data-[collapsible=icon]:opacity-0 group-data-[collapsible=icon]:transition-opacity group-data-[collapsible=icon]:group-hover/header:opacity-100">
              <SidebarTrigger />
            </div>
          </div>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                render={
                  <Link
                    href="/chat"
                    onClick={(event) => {
                      event.preventDefault();
                      setConfirmNewConversation(true);
                    }}
                  />
                }
                className="h-10 bg-brand-accent text-brand-accent-foreground hover:bg-brand-accent/90 hover:text-brand-accent-foreground group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!justify-center group-data-[collapsible=icon]:!p-2"
                size="lg"
                tooltip="Nueva consulta"
              >
                <MessageSquarePlusIcon />
                <span className="group-data-[collapsible=icon]:hidden">
                  Nueva consulta
                </span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
      </Sidebar>
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
