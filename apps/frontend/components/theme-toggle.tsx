"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <Button
      className="size-11 rounded-xl text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-foreground dark:hover:bg-sidebar-accent"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      size="icon-lg"
      title="Cambiar tema"
      type="button"
      variant="ghost"
    >
      <Sun aria-hidden="true" className="hidden dark:block" />
      <Moon aria-hidden="true" className="block dark:hidden" />
      <span className="sr-only hidden dark:inline">Activar tema claro</span>
      <span className="sr-only dark:hidden">Activar tema oscuro</span>
    </Button>
  );
}
