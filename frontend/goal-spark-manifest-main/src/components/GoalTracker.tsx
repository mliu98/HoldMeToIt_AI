import { useState, useEffect } from "react";
import { ChatInterface } from "./ChatInterface";
import { GoalPanel } from "./GoalPanel";

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

interface GoalData {
  goal: string;
  deadline: string;
  timelineTasks: TimelineTask[];
}

export function GoalTracker() {
  const [showGoalPanel, setShowGoalPanel] = useState(false);
  const [timelineTasks, setTimelineTasks] = useState<TimelineTask[]>([]);
  const [goalData, setGoalData] = useState<GoalData>({
    goal: "Complete the React project by the end of the month",
    deadline: "April 30, 2025",
    timelineTasks: []
  });
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "assistant"; content: string }[]>([]);

  const handleTimelineUpdate = (tasks: TimelineTask[]) => {
    console.log("GoalTracker received timeline tasks:", tasks);
    setTimelineTasks(tasks);
    
    // Update the goalData with the new timeline tasks
    setGoalData(prev => ({
      ...prev,
      timelineTasks: tasks
    }));
  };

  const handleGoalDataUpdate = (newGoalData: GoalData) => {
    console.log("GoalTracker received goal data update:", newGoalData);
    setGoalData(newGoalData);
  };

  const handleViewGoalTracker = () => {
    console.log("View Goal Tracker button clicked");
    setShowGoalPanel(true);
  };

  const handleBackClick = () => {
    setShowGoalPanel(false);
  };

  const handleReturnToChat = () => {
    console.log("Return to Chat button clicked");
    setShowGoalPanel(false);
  };

  const handleChatMessage = (message: { role: "user" | "assistant"; content: string }) => {
    setChatHistory(prev => [...prev, message]);
  };

  return (
    <div className="h-full">
      {showGoalPanel ? (
        <GoalPanel 
          timelineTasks={goalData.timelineTasks}
          goal={goalData.goal}
          deadline={goalData.deadline}
          onBackClick={handleBackClick}
          onReturnToChat={handleReturnToChat}
        />
      ) : (
        <ChatInterface 
          onTimelineUpdate={handleTimelineUpdate} 
          onGoalDataUpdate={handleGoalDataUpdate}
          onViewGoalTracker={handleViewGoalTracker}
          initialMessages={chatHistory}
          onMessage={handleChatMessage}
        />
      )}
    </div>
  );
} 