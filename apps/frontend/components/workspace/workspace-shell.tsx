"use client";

import type { CSSProperties, ReactNode } from "react";

import {
  SidebarInset,
  SidebarProvider,
  useSidebar,
} from "@/components/ui/sidebar";
import { WorkspaceSidebar } from "@/components/workspace/workspace-sidebar";

export function WorkspaceShell({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider className="h-svh overflow-hidden">
      <WorkspaceShellContent>{children}</WorkspaceShellContent>
    </SidebarProvider>
  );
}

function WorkspaceShellContent({ children }: { children: ReactNode }) {
  const { isMobile, state } = useSidebar();
  const sidebarOffset = isMobile ? "0px" : state === "collapsed" ? "3rem" : "16rem";

  return (
    <>
      <WorkspaceSidebar />
      <SidebarInset className="h-svh min-h-0 overflow-hidden">
        <div
          className="relative flex h-[100dvh] min-w-0 flex-1 flex-col overflow-hidden bg-background"
          style={{ "--workspace-sidebar-offset": sidebarOffset } as CSSProperties}
        >
          <main className="relative z-0 flex min-h-0 flex-1 flex-col overflow-hidden">
            {children}
          </main>
        </div>
      </SidebarInset>
    </>
  );
}
