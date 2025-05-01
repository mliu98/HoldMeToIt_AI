import { useState, useEffect } from "react";
import { ArrowLeft, Calendar, CheckCircle, Circle, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GoalStep } from "./GoalStep";

interface TimelineTask {
  id: number;
  text: string;
  date: string;
  subtasks: {
    id: number;
    text: string;
    completed: boolean;
  }[];
}

interface GoalPanelProps {
  timelineTasks?: TimelineTask[];
  goal?: string;
  deadline?: string;
  onBackClick?: () => void;
  onReturnToChat?: () => void;
}

export function GoalPanel({ 
  timelineTasks: propTimelineTasks, 
  goal: propGoal,
  deadline: propDeadline,
  onBackClick, 
  onReturnToChat 
}: GoalPanelProps) {
  const [goal, setGoal] = useState(propGoal || "Complete the React project by the end of the month");
  const [deadline, setDeadline] = useState(propDeadline || "April 30, 2025");
  const [timelineTasks, setTimelineTasks] = useState<TimelineTask[]>([
    {
      id: 1,
      text: "Project Setup Phase",
      date: "April 19-21",
      subtasks: [
        { id: 1, text: "Define project scope and requirements", completed: true },
        { id: 2, text: "Set up development environment", completed: true }
      ]
    },
    {
      id: 2,
      text: "Development Phase",
      date: "April 22-26",
      subtasks: [
        { id: 3, text: "Create component structure", completed: false },
        { id: 4, text: "Implement core functionality", completed: false }
      ]
    },
    {
      id: 3,
      text: "Testing Phase",
      date: "April 27-30",
      subtasks: [
        { id: 5, text: "Test and debug", completed: false },
        { id: 6, text: "Final review and deployment", completed: false }
      ]
    }
  ]);

  // Update goal and deadline when props change
  useEffect(() => {
    if (propGoal) {
      setGoal(propGoal);
    }
    if (propDeadline) {
      setDeadline(propDeadline);
    }
  }, [propGoal, propDeadline]);

  // Update timeline tasks when prop changes
  useEffect(() => {
    console.log("GoalPanel received propTimelineTasks:", propTimelineTasks);
    console.log("GoalPanel propTimelineTasks length:", propTimelineTasks?.length || 0);
    
    if (propTimelineTasks && propTimelineTasks.length > 0) {
      console.log("Setting timeline tasks in GoalPanel");
      setTimelineTasks(propTimelineTasks);
      console.log("GoalPanel state after update:", propTimelineTasks);
    } else {
      console.log("GoalPanel: No timeline tasks received or empty array");
    }
  }, [propTimelineTasks]);

  const toggleSubtask = (taskId: number, subtaskId: number) => {
    // Implementation would go here if state management was needed
    console.log("Toggle subtask", taskId, subtaskId);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-white rounded-t-lg">
        <h2 className="font-semibold text-lg">Goal Timeline</h2>
      </div>
      
      <div className="flex-1 p-4 bg-goal-peach/20 overflow-auto">
        <div className="mb-6">
          <h3 className="text-sm text-muted-foreground uppercase tracking-wider mb-1">My Goal</h3>
          <p className="text-xl font-medium">{goal}</p>
        </div>
        
        <div className="mb-6">
          <h3 className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Deadline</h3>
          <div className="flex items-center gap-2 text-lg">
            <Calendar size={18} className="text-goal-purple" />
            <span>{deadline}</span>
          </div>
        </div>
        
        <div>
          <h3 className="text-sm text-muted-foreground uppercase tracking-wider mb-3">Timeline & Tasks</h3>
          <div className="relative space-y-6">
            {timelineTasks.map((task, index) => (
              <div key={task.id} className="relative">
                <div className="flex items-start gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-goal-purple text-white flex items-center justify-center">
                      {index + 1}
                    </div>
                    {index < timelineTasks.length - 1 && (
                      <div className="w-0.5 h-full bg-goal-purple/20 absolute top-8 left-[15px]" />
                    )}
                  </div>
                  <div className="flex-1 bg-white rounded-lg p-4 shadow-sm">
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-medium">{task.text}</h4>
                      <span className="text-sm text-muted-foreground">{task.date}</span>
                    </div>
                    <div className="space-y-2">
                      {task.subtasks && task.subtasks.length > 0 ? (
                        task.subtasks.map(subtask => (
                          <GoalStep
                            key={subtask.id}
                            step={subtask}
                            onClick={() => toggleSubtask(task.id, subtask.id)}
                          />
                        ))
                      ) : (
                        <div className="text-sm text-muted-foreground italic">
                          No subtasks defined yet
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      <div className="p-3 border-t bg-white rounded-b-lg flex justify-between">
        <Button 
          variant="outline" 
          size="sm" 
          className="flex items-center gap-1"
          onClick={onBackClick}
        >
          <ArrowLeft size={14} />
          <span>Back to Goals</span>
        </Button>
        
        <Button 
          variant="outline" 
          size="sm" 
          className="flex items-center gap-1"
          onClick={onReturnToChat}
        >
          <MessageSquare size={14} />
          <span>Return to Chat</span>
        </Button>
      </div>
    </div>
  );
}
