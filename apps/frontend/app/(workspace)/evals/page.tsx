import type { Metadata } from "next";

import { EvalsPage } from "@/components/workspace/evals-page";

export const metadata: Metadata = {
  title: "Evaluaciones RAGAS · DIGEMID",
};

export default function EvalsRoute() {
  return <EvalsPage />;
}
