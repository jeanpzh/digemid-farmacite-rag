import type { Metadata } from "next";

import { SettingsPage } from "@/components/workspace/settings-page";

export const metadata: Metadata = {
  title: "Configuración · DIGEMID",
};

export default function SettingsRoute() {
  return <SettingsPage />;
}
