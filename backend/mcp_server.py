from typing import Any, List, Dict
import httpx
from mcp.server.fastmcp import FastMCP
import json
from datetime import datetime, timedelta
import anthropic
from dotenv import load_dotenv

# Initialize FastMCP server
mcp = FastMCP("goal_tracker")
load_dotenv()

# Initialize Anthropic client
client = anthropic.Anthropic()

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
        system_prompt = """You are a goal breakdown assistant. Break down the given goal into 5 specific tasks.
        For each task, provide:
        1. A clear goal title
        2. Detailed description
        3. Estimated duration in days
        4. Dependencies (if any)
        5. Key milestones
        
        IMPORTANT: Your response must be a valid JSON array containing task objects. Each task object must have these exact fields:
        {
            "title": "string",
            "description": "string",
            "estimated_duration": "X days",
            "dependencies": ["string"],
            "milestones": ["string"]
        }
        
        Example response format:
        [
            {
                "title": "Task 1",
                "description": "Description of task 1",
                "estimated_duration": "5 days",
                "dependencies": [],
                "milestones": ["Milestone 1", "Milestone 2"]
            }
        ]
        
        Do not include any additional text or explanation outside the JSON array."""

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
    # Initialize and run the server
    # mcp.run(transport='stdio')
    print(break_down_goal("write a book about my life"))
    