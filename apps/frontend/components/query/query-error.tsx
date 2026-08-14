import { CircleAlert } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function QueryError({ message }: { message: string }) {
  return (
    <Alert variant="destructive">
      <CircleAlert aria-hidden="true" />
      <AlertTitle>No pudimos completar la consulta</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
