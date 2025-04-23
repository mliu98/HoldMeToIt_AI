
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  message: string;
  isBot: boolean;
}

export function ChatMessage({ message, isBot }: ChatMessageProps) {
  return (
    <div
      className={cn(
        "mb-3 max-w-[80%] rounded-2xl p-3 animate-fade-in",
        isBot
          ? "bg-white shadow-md self-start rounded-tl-sm"
          : "gradient-purple text-white self-end rounded-tr-sm"
      )}
    >
      {message}
    </div>
  );
}
