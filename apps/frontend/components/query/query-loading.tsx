import { Shimmer } from "@/components/ai-elements/shimmer";
import { Message, MessageContent } from "@/components/ai-elements/message";

export function QueryLoading() {
  return (
    <Message from="assistant">
      <MessageContent>
        <Shimmer>Analizando la documentación...</Shimmer>
      </MessageContent>
    </Message>
  );
}
