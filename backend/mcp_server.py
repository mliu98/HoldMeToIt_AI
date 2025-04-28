from typing import Any, List, Dict
import httpx
from mcp.server.fastmcp import FastMCP
import json
from datetime import datetime, timedelta
import anthropic
from dotenv import load_dotenv
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
try:
    mcp = FastMCP("goal_tracker")
    logger.info("FastMCP initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize FastMCP: {str(e)}")
    sys.exit(1)
# Load environment variables
try:
    load_dotenv()
    logger.info("Environment variables loaded")
except Exception as e:
    logger.error(f"Failed to load environment variables: {str(e)}")
    sys.exit(1)

# Initialize Anthropic client
try:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)
    logger.info("Anthropic client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Anthropic client: {str(e)}")
    sys.exit(1)

def format_timeline(tasks: List[Dict[str, Any]]) -> str:
    """Format the timeline data into a readable string."""
    timeline = []
    for task in tasks:
        task_str = f"""
Task: {task['title']}
Description: {task['description']}
Estimated Duration: {task['estimated_duration']}
Dependencies: {', '.join(task['dependencies']) if task['dependencies'] else 'None'}
Milestones: {', '.join(task['milestones'])}
"""
        timeline.append(task_str)
    return "\n---\n".join(timeline)

@mcp.tool()
def break_down_goal(goal: str) -> str:
    """Break down a user's goal into tasks and generate a timeline.
    
    Args:
        goal: The user's goal or objective to break down
    """
    try:
        # Use Claude to break down the goal
        system_prompt = """
        You are a goal intake assistant that helps users define and structure their goals using best-practice goal-setting frameworks like SMART and Atomic Habits.

Your objective is to **converse naturally** with the user and **progressively collect the required parameters** for the goal. Only ask for one thing at a time.

### Framework Use
- If the goal sounds like a **one-time project**, use the **SMART** framework.
- If the goal is about **habits or routines**, use **Atomic Habits**.
- You do NOT need to tell the user which framework you’re using — just guide them through the questions naturally.

### Required Parameters
You must collect:
- `goal`: The user's goal in their own words.
- `specific`, `measurable`, `achievable`, `relevant`, `time_bound`: (if SMART-style goal)
- `cue`, `habit`, `reward`: (if Atomic Habits-style)
- `start_date`: When they want to start
- `end_date`: When they want to finish (or build a timeline from duration)

### Flow Rules
- Be conversational: Ask friendly, direct questions one at a time.
- Infer which framework to use based on the goal.
- Keep track of what’s been answered.
- Once all required parameters are collected, summarize them in **natural language** and then in a **valid JSON object** like below:
```json
{
  "goal": "string",
  "framework": "SMART or Atomic Habits",
  "parameters": {
    "specific": "...",
    "measurable": "...",
    "achievable": "...",
    "relevant": "...",
    "time_bound": "..."
  },
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD"
}

        """


        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Break down this goal into specific tasks and return ONLY a JSON array: {goal}"
                }
            ]
        )
        
        # Get the response text and clean it
        response_text = response.content[0].text.strip()
        
        # Debug: Print the raw response
        print("Raw response:", response_text)
        
        # Try to find JSON array in the response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON array found in response")
            
        json_str = response_text[start_idx:end_idx]
        
        # Parse the JSON
        tasks_data = json.loads(json_str)
        
        if not isinstance(tasks_data, list):
            raise ValueError("Response is not a JSON array")
        
        # Calculate start and end dates for each task
        current_date = datetime.now()
        for task in tasks_data:
            task['start_date'] = current_date.strftime('%Y-%m-%d')
            duration_days = int(task['estimated_duration'].split()[0])
            end_date = current_date + timedelta(days=duration_days)
            task['end_date'] = end_date.strftime('%Y-%m-%d')
            current_date = end_date + timedelta(days=1)  # Add 1 day buffer between tasks
        
        # Create a standardized response format
        response_data = {
            "goal": goal,
            "tasks": tasks_data,
            "total_duration": sum(int(task['estimated_duration'].split()[0]) for task in tasks_data),
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Return both formatted string and JSON for flexibility
        return {
            "formatted": format_timeline(tasks_data),
            "json": json.dumps(response_data, indent=2)
        }
        
    except Exception as e:
        return f"Error breaking down goal: {str(e)}\nResponse text: {response_text if 'response_text' in locals() else 'No response'}"

if __name__ == "__main__":
    try:
        logger.info("Starting MCP server...")
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        sys.exit(1)
    # print(break_down_goal("write a book about my life"))
    