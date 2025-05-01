
import { useState } from "react";
import { Bell, Mail, MessageSquare } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function ReminderSettings() {
  const [emailReminders, setEmailReminders] = useState(true);
  const [smsReminders, setSmsReminders] = useState(false);
  
  const handleFinish = () => {
    toast.success("Reminder settings saved successfully!");
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-white rounded-t-lg">
        <h2 className="font-semibold text-lg flex items-center gap-2">
          <Bell size={18} className="text-goal-purple" />
          <span>Reminder Settings</span>
        </h2>
      </div>
      
      <div className="flex-1 p-4 bg-goal-blue/20">
        <div className="space-y-6">
          <div className="flex flex-col gap-1.5">
            <h3 className="text-sm text-muted-foreground uppercase tracking-wider">
              Notification Methods
            </h3>
            <p className="text-sm text-muted-foreground mb-2">
              Choose how you'd like to receive reminders about your goal progress.
            </p>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-white p-3 rounded-lg">
                <div className="flex items-center gap-3">
                  <Mail size={18} className="text-goal-purple" />
                  <div>
                    <p className="font-medium">Email Reminders</p>
                    <p className="text-sm text-muted-foreground">Receive updates in your inbox</p>
                  </div>
                </div>
                <Switch 
                  checked={emailReminders} 
                  onCheckedChange={setEmailReminders} 
                  className="data-[state=checked]:bg-goal-purple"
                />
              </div>
              
              <div className="flex items-center justify-between bg-white p-3 rounded-lg">
                <div className="flex items-center gap-3">
                  <MessageSquare size={18} className="text-goal-purple" />
                  <div>
                    <p className="font-medium">SMS Reminders</p>
                    <p className="text-sm text-muted-foreground">Get text message alerts</p>
                  </div>
                </div>
                <Switch 
                  checked={smsReminders} 
                  onCheckedChange={setSmsReminders} 
                  className="data-[state=checked]:bg-goal-purple"
                />
              </div>
            </div>
          </div>
          
          <div className="flex flex-col gap-1.5">
            <h3 className="text-sm text-muted-foreground uppercase tracking-wider">
              Reminder Frequency
            </h3>
            
            <div className="bg-white p-3 rounded-lg">
              <select className="w-full p-2 rounded-md border border-input">
                <option value="daily">Daily</option>
                <option value="weekdays">Weekdays Only</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      
      <div className="p-3 border-t bg-white rounded-b-lg">
        <Button 
          onClick={handleFinish} 
          className="w-full bg-goal-purple hover:bg-goal-purple/90"
        >
          Save Settings
        </Button>
      </div>
    </div>
  );
}
