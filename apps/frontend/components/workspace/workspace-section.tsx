import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

export function WorkspaceSection({
  className,
  ...props
}: ComponentProps<"section">) {
  return (
    <section
      className={cn(
        "mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-16 md:px-8 md:py-24",
        className,
      )}
      {...props}
    />
  );
}
