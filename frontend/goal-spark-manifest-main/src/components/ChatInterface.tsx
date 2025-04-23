import { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatMessage } from "./ChatMessage";

interface Message {
  text: string;
  isBot: boolean;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      text: "Hi there! I'm your Goal Tracking Assistant. You can tell me about your goal and I will break it down for you.",
      isBot: true,
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    // Add user message
    const newMessages = [...messages, { text: inputValue, isBot: false }];
    setMessages(newMessages);
    setInputValue("");
    setIsLoading(true);

    try {
      // Send query to the backend which connects to MCP
      const response = await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: inputValue
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setMessages([...newMessages, { text: data.response, isBot: true }]);
      } else {
        setMessages([...newMessages, { text: `Error: ${data.error}`, isBot: true }]);
      }
    } catch (error) {
      setMessages([...newMessages, { text: `Error: Unable to connect to the server. Make sure the Flask backend is running.`, isBot: true }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !isLoading) {
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b bg-white rounded-t-lg">
        <h2 className="font-semibold text-lg">Weather Assistant</h2>
        <p className="text-sm text-muted-foreground">Ask about weather alerts or forecasts</p>
      </div>
      
      <div className="flex-1 overflow-auto p-4 bg-goal-blue/20 flex flex-col">
        {messages.map((msg, index) => (
          <ChatMessage key={index} message={msg.text} isBot={msg.isBot} />
        ))}
        {isLoading && (
          <div className="text-center text-sm text-muted-foreground">
            Processing your request...
          </div>
        )}
      </div>
      
      <div className="p-3 border-t bg-white rounded-b-lg flex items-center gap-2">
        <Input
          placeholder="Ask about weather alerts or forecasts..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1 focus-visible:ring-goal-purple"
          disabled={isLoading}
        />
        <Button 
          size="icon" 
          onClick={handleSendMessage} 
          className="bg-goal-purple hover:bg-goal-purple/90"
          disabled={isLoading}
        >
          <Send size={18} />
        </Button>
      </div>
    </div>
  );
}