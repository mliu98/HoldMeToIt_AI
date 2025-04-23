
import { CheckCircle, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

interface GoalStepProps {
  step: {
    id: number;
    text: string;
    completed: boolean;
  };
  onClick: (id: number) => void;
}

export function GoalStep({ step, onClick }: GoalStepProps) {
  return (
    <div 
      className={cn(
        "flex items-center gap-3 p-3 rounded-lg transition-all cursor-pointer",
        step.completed ? "bg-goal-mint/40" : "bg-white hover:bg-goal-purple/5"
      )}
      onClick={() => onClick(step.id)}
    >
      {step.completed ? (
        <CheckCircle className="text-green-500 flex-shrink-0" size={20} />
      ) : (
        <Circle className="text-goal-purple flex-shrink-0" size={20} />
      )}
      <span className={cn(step.completed && "line-through text-muted-foreground")}>
        {step.text}
      </span>
    </div>
  );
}
