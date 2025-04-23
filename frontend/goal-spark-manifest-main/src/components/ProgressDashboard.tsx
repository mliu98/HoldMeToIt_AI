
import { CalendarDays } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface Task {
  id: number;
  text: string;
  date: string;
  completed: boolean;
}

export function ProgressDashboard() {
  const progressPercentage = 40;
  const upcomingTasks: Task[] = [
    { id: 1, text: "Create component structure", date: "Today", completed: false },
    { id: 2, text: "Implement core functionality", date: "Tomorrow", completed: false },
    { id: 3, text: "Test and debug", date: "Apr. 28", completed: false }
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-white rounded-t-lg">
        <h2 className="font-semibold text-lg">Progress Dashboard</h2>
      </div>
      
      <div className="flex-1 p-4 bg-goal-mint/20 overflow-auto">
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm text-muted-foreground uppercase tracking-wider">
              Goal Progress
            </h3>
            <span className="font-semibold text-lg">{progressPercentage}%</span>
          </div>
          
          <Progress 
            value={progressPercentage} 
            className={cn(
              "h-3 bg-white [&>div]:bg-goal-purple",
              progressPercentage >= 100 && "[&>div]:bg-green-500"
            )}
          />
        </div>
        
        <div>
          <h3 className="text-sm text-muted-foreground uppercase tracking-wider mb-3">
            Upcoming Tasks
          </h3>
          
          <div className="space-y-3">
            {upcomingTasks.map(task => (
              <div key={task.id} className="flex items-start gap-3 bg-white p-3 rounded-lg shadow-sm">
                <CalendarDays size={18} className="text-goal-purple mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-medium">{task.text}</p>
                  <p className="text-sm text-muted-foreground">{task.date}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
