import { Link } from "react-router-dom";
import { ChatInterface } from "@/components/ChatInterface";
import { GoalPanel } from "@/components/GoalPanel";
import { ProgressDashboard } from "@/components/ProgressDashboard";
import { ReminderSettings } from "@/components/ReminderSettings";
import { Button } from "@/components/ui/button";

const Index = () => {
  // This is a placeholder function for the original ChatInterface
  const handleTimelineUpdate = () => {
    console.log("Timeline update requested");
  };

  return (
    <div className="min-h-screen bg-goal-bg p-4 md:p-6">
      <header className="max-w-7xl mx-auto mb-6">
        <h1 className="text-3xl font-bold text-goal-purple">GoalSpark</h1>
        <p className="text-muted-foreground">Track, plan, and achieve your goals</p>
      </header>

      <main className="max-w-7xl mx-auto space-y-6">
        <div className="shadow-card rounded-lg bg-white h-[400px] animate-slide-up">
          {/* <ChatInterface onTimelineUpdate={handleTimelineUpdate} /> */}
        </div>
        
        {/* <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="shadow-card rounded-lg bg-white h-[500px] animate-slide-up md:col-span-2" style={{ animationDelay: "0.1s" }}>
            <GoalPanel />
          </div>
          
          <div className="shadow-card rounded-lg bg-white h-[500px] animate-slide-up" style={{ animationDelay: "0.2s" }}>
            <ProgressDashboard />
          </div>
          
          <div className="shadow-card rounded-lg bg-white h-[500px] animate-slide-up md:col-span-3" style={{ animationDelay: "0.3s" }}>
            <ReminderSettings />
          </div>
        </div> */}
        
        <div className="flex justify-center mt-6">
          <Link to="/goal-tracker">
            <Button className="bg-goal-purple hover:bg-goal-purple/90">
              Open Goal Tracker
            </Button>
          </Link>
        </div>
      </main>
    </div>
  );
};

export default Index;
