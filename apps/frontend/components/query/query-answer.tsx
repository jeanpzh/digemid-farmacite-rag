import {
  MessageResponse,
} from "@/components/ai-elements/message";

export function QueryAnswer({ answer }: { answer: string }) {
  return (
    <MessageResponse className="max-w-[72ch] text-[15px] leading-7" isAnimating={false}>
      {answer}
    </MessageResponse>
  );
}
