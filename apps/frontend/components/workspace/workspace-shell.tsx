"use client";

import type { ReactNode } from "react";

import { WorkspaceSidebar } from "@/components/workspace/workspace-sidebar";

export function WorkspaceShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-svh min-h-0 w-full overflow-hidden bg-background">
      <WorkspaceSidebar />
      <main className="relative z-0 flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        {children}
      </main>
    </div>
  );
}
