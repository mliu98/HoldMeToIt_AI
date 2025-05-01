import { useState, useRef, useEffect } from "react";
import { Send, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import ReactMardown from "react-markdown"

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

interface ChatInterfaceProps {
  onTimelineUpdate: (tasks: TimelineTask[]) => void;
  onGoalDataUpdate?: (goalData: GoalData) => void;
  onViewGoalTracker?: () => void;
  initialMessages?: { role: "user" | "assistant"; content: string }[];
  onMessage?: (message: { role: "user" | "assistant"; content: string }) => void;
}

export function ChatInterface({ 
  onTimelineUpdate, 
  onGoalDataUpdate,
  onViewGoalTracker,
  initialMessages = [],
  onMessage
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string }[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showGoalTrackerButton, setShowGoalTrackerButton] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize messages from props if provided
  useEffect(() => {
    if (initialMessages.length > 0) {
      setMessages(initialMessages);
    }
  }, [initialMessages]);

  // Debug log for showGoalTrackerButton state
  useEffect(() => {
    console.log("showGoalTrackerButton state changed:", showGoalTrackerButton);
  }, [showGoalTrackerButton]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);
    setShowGoalTrackerButton(false);
    console.log("Reset showGoalTrackerButton to false");

    // Add user message to chat
    const newUserMessage = { role: "user" as const, content: userMessage };
    setMessages(prev => [...prev, newUserMessage]);
    
    // Notify parent component about the new message
    if (onMessage) {
      onMessage(newUserMessage);
    }

    try {
      const response = await fetch("http://localhost:5000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: userMessage }),
      });

      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      const data = await response.json();
      console.log("Chat response:", data);
      console.log("tool_results exists:", !!data.tool_results);
      console.log("tool_results value:", data.tool_results);

      // Add assistant message to chat
      const newAssistantMessage = { role: "assistant" as const, content: data.response };
      setMessages(prev => [...prev, newAssistantMessage]);
      
      // Notify parent component about the new message
      if (onMessage) {
        onMessage(newAssistantMessage);
      }

      // Parse timeline tasks from tool_results if available
      if (data.tool_results) {
        try {
          // Parse the tool_results JSON string
          const toolResults = JSON.parse(data.tool_results);
          console.log("Parsed tool_results:", toolResults);
          
          // Find the break_down_goal tool result
          const breakDownGoalResult = toolResults.find(
            (result: any) => result.tool_name === "break_down_goal"
          );
          
          if (breakDownGoalResult) {
            console.log("Found break_down_goal result:", breakDownGoalResult);
            
            // Parse the result string which contains the goal breakdown
            const goalBreakdown = JSON.parse(breakDownGoalResult.result);
            console.log("Parsed goal breakdown:", goalBreakdown);
            
            // Extract goal and deadline
            const goalData: GoalData = {
              goal: goalBreakdown.goal || "Unspecified goal",
              deadline: goalBreakdown.deadline || "No deadline specified",
              timelineTasks: []
            };
            
            // Check if the parsed result has timelineTasks property
            if (goalBreakdown.timelineTasks && Array.isArray(goalBreakdown.timelineTasks)) {
              console.log("Found timelineTasks array:", goalBreakdown.timelineTasks);
              console.log("Length:", goalBreakdown.timelineTasks.length);
              
              if (goalBreakdown.timelineTasks.length > 0) {
                console.log("Calling onTimelineUpdate with tasks:", goalBreakdown.timelineTasks);
                onTimelineUpdate(goalBreakdown.timelineTasks);
                
                // Update goalData with timeline tasks
                goalData.timelineTasks = goalBreakdown.timelineTasks;
                
                // Notify parent component about the goal data update
                if (onGoalDataUpdate) {
                  onGoalDataUpdate(goalData);
                }
                
                console.log("Setting showGoalTrackerButton to true");
                setShowGoalTrackerButton(true);
              } else {
                console.log("timelineTasks array is empty");
              }
            } else {
              console.log("No timelineTasks property found in goal breakdown");
            }
          } else {
            console.log("No break_down_goal tool result found");
          }
        } catch (error) {
          console.error("Error parsing tool_results:", error);
        }
      } else {
        console.log("No tool_results found in response");
      }
    } catch (error) {
      console.error("Error:", error);
      const errorMessage = { role: "assistant" as const, content: "Sorry, I encountered an error. Please try again." };
      setMessages(prev => [...prev, errorMessage]);
      
      // Notify parent component about the error message
      if (onMessage) {
        onMessage(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewGoalTracker = () => {
    console.log("handleViewGoalTracker called");
    if (onViewGoalTracker) {
      console.log("Calling onViewGoalTracker prop");
      onViewGoalTracker();
    } else {
      console.log("onViewGoalTracker prop is not defined");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b bg-white rounded-t-lg">
        <h2 className="font-semibold text-lg">Goal Tracking Assistant</h2>
        <p className="text-sm text-muted-foreground">Talk about your goal</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === "user"
                  ? "bg-goal-purple text-white"
                  : "bg-white border"
              }`}
            >
              <ReactMardown>{message.content}</ReactMardown>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {showGoalTrackerButton && (
        <div className="p-2 border-t bg-white">
          <Button 
            onClick={handleViewGoalTracker}
            className="w-full bg-goal-purple hover:bg-goal-purple/90 text-white"
          >
            <span>View Your Goal Tracker</span>
            <ArrowRight size={16} className="ml-2" />
          </Button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-4 border-t bg-white">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
          />
          <Button type="submit" disabled={isLoading}>
            <Send size={16} />
          </Button>
        </div>
      </form>
    </div>
  );
}