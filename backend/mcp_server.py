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
from calendar_functions import schedule_goal_tasks
from reminder_agent import ReminderTool
from email_scheduler import EmailScheduler
import asyncio

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

def break_down_goal(goal: str) -> str:
    """
    Break down a user's goal into tasks through conversation and generate a timeline.
    """
    print("DEBUG: break_down_goal function called!", flush=True)  # Debug print at start
    try:
        # Use Claude to break down the goal
        system_prompt = """
        You are a compassionate, insightful Goal Achievement Coach with expertise in personal development and behavioral psychology. Your approach combines warmth with analytical precision, making users feel both supported and empowered.
        When interacting with users, create a personalized coaching experience that feels like you're genuinely getting to know them as individuals. Speak directly to them using "you" language, acknowledge their unique circumstances, and respond with empathy to their specific situation.

        Your tone should be:
        - Warm and encouraging, like a supportive friend
        - Insightful and thoughtful, asking questions that make users reflect deeper
        - Positive but realistic, focusing on progress rather than perfection
        - Conversational and natural, avoiding corporate or clinical language

        **IMPORTANT PROCESS INSTRUCTION:**
        1. FIRST: Have a natural, conversational dialogue with the user to collect all required information about their goal. Do not output any JSON during this information-gathering phase.
        2. CONTINUE the conversation until you have sufficient information for all JSON fields.
        3. ONLY AFTER all information is collected, your FINAL response should consist EXCLUSIVELY of the JSON object with no additional text or explanation.

        During the conversation phase, build rapport and understand the person behind the goal. Ask about their motivation and previous experiences with similar goals. Make them feel seen and understood before diving into the structured analysis.
        Remember that goal-setting is both practical and emotional - address both aspects in your approach. Celebrate their initiative in setting this goal and express genuine confidence in their ability to achieve it.
        Help users transform their goals into actionable plans by gathering information on the following key components:

        1. GOAL STATEMENT: Extract a clear, specific statement of what the user wants to accomplish. Refine vague goals into concrete outcomes.
        2. SUCCESS METRICS: Identify how progress and completion will be measured. What specific indicators will show that the goal has been achieved?
        3. IMPORTANCE CONTEXT: Understand why this goal matters to the user. What motivated them to pursue this? What impact will accomplishing this goal have?
        4. CURRENT STATE: Assess where the user is currently in relation to this goal. What's their starting point?
        5. SUB-TASKS: Break down the goal into smaller, actionable components that can be accomplished incrementally.
        6. POTENTIAL OBSTACLES: Anticipate challenges or barriers that might prevent goal achievement.
        7. RESOURCES NEEDED: Identify tools, information, skills, or support the user will need to succeed.
        8. START DATE: Determine when work on the goal should begin. Use YYYY-MM-DD format.
        9. END DATE: Establish a deadline for completing the goal. Use YYYY-MM-DD format.

        If the user doesn't provide enough information for any component, ask specific follow-up questions to gather that information in a way that feels like a meaningful conversation rather than an interrogation.
        After collecting all necessary information through conversation, your FINAL response should be ONLY the completed JSON object following this structure with NO additional text:

        {
        "goal_statement":     "Clear statement of the desired outcome",
        "success_metrics":    "How progress/completion will be measured",
        "importance_context": "Why this matters/motivation",
        "current_state":      "Assessment of starting point",
        "sub_tasks":          ["Breakdown into actionable components"],
        "potential_obstacles":"Anticipated challenges",
        "resources_needed":   "Tools, information, or support required",
        "start_date":         "YYYY-MM-DD",
        "end_date":           "YYYY-MM-DD"
        }
        """

        # Initialize conversation history
        conversation_history = [
            {
                "role": "user",
                "content": f"Let's break down this goal: {goal}"
            }
        ]

        # Continue conversation until we get a complete JSON response
        while True:
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                temperature=0.7,
                system=system_prompt,
                messages=conversation_history
            )
           
            response_text = response.content[0].text.strip()
           
            # Check if the response contains a complete JSON object
            if response_text.startswith('{') and response_text.endswith('}'):
                try:
                    # Validate that it's proper JSON
                    json.loads(response_text)
                    return json.dumps({
                        "is_complete": True,
                        "json_data": json.loads(response_text),
                        "response": response_text,
                        "conversation": [
                            {"role": msg["role"], "content": msg["content"]}
                            for msg in conversation_history
                        ]
                    })
                except json.JSONDecodeError:
                    # If it's not valid JSON, continue the conversation
                    conversation_history.append({
                        "role": "assistant",
                        "content": response_text
                    })
                    conversation_history.append({
                        "role": "user",
                        "content": "Please provide the complete information in JSON format only."
                    })
            else:
                # Add the response to conversation history and continue
                conversation_history.append({
                    "role": "assistant",
                    "content": response_text
                })
                conversation_history.append({
                    "role": "user",
                    "content": "Please continue gathering information about the goal."
                })
       
    except Exception as e:
        return f"Error breaking down goal: {str(e)}"
    
# @mcp.tool()
def process_goal(goal: str) -> str:
    """Process a goal through the entire workflow:
    1. Break down the goal into tasks
    2. Schedule tasks as calendar events
    3. Generate reminders for the events
    4. Schedule email notifications
        
    Args:
        goal: The user's goal or objective to process
    """
    try:
        # Step 1: Break down the goal
        goal_breakdown = break_down_goal(goal)
        if isinstance(goal_breakdown, str) and goal_breakdown.startswith("Error"):
            return goal_breakdown
            
        # Parse the goal_breakdown response
        goal_breakdown_data = json.loads(goal_breakdown)
        if not goal_breakdown_data.get("is_complete", False):
            return "Error: Goal breakdown was not completed successfully"
            
        goal_data = goal_breakdown_data["json_data"]
        
        # Step 2: Schedule tasks as calendar events
        calendar_events = schedule_goal_tasks(goal_data, client)
        if not calendar_events:
            return "Error: Failed to schedule calendar events"
            
        # Step 3: Generate reminders
        reminder_tool = ReminderTool(client)
        reminder_result = reminder_tool.generate_reminders_for_calendar_events(
            objective=goal_data["goal_statement"],
            task_data=goal_data,
            calendar_events=calendar_events
        )
        
        if not reminder_result["success"]:
            return f"Error generating reminders: {reminder_result['message']}"
            
        # Step 4: Schedule email notifications
        email_scheduler = EmailScheduler()
        reminders = reminder_tool.get_all_reminders()
        post_event_emails = reminder_tool.get_all_post_event_emails()
        
        # Schedule all reminders and emails
        email_scheduler.schedule_reminders(reminders, calendar_events)
        email_scheduler.schedule_post_event_emails(post_event_emails, calendar_events)
        
        # Wait for all scheduled tasks to complete
        email_scheduler.wait_for_completion()
        
        return {
            "message": "Goal processed successfully",
            "goal_breakdown": goal_breakdown,
            "calendar_events": calendar_events,
            "reminders": reminders,
            "post_event_emails": post_event_emails
        }
        
    except Exception as e:
        logger.error(f"Error processing goal: {str(e)}")
        return f"Error processing goal: {str(e)}"

async def main():
    try:
        # logger.info("Starting MCP server...")
        # mcp.run(transport='stdio')
        result = process_goal("""
                           I want to run 5k, here are my exact details this should be a 1 shot interaction.
{
  "goal_statement":     "To complete a 5K run within 30 minutes",
  "success_metrics":    "Completing the 5K run under the set time and tracking progress through weekly training times",
  "importance_context": "Improving physical fitness and achieving a personal milestone for confidence and health benefits",
  "current_state":      "Currently able to jog 2 miles at an average pace of 11 minutes per mile, with irregular workout routines",
  "sub_tasks":          [
                          "Research and follow a structured 8-week training plan",
                          "Incorporate strength training twice a week",
                          "Gradually increase weekly running distance",
                          "Practice pacing strategies during runs",
                          "Monitor diet and hydration to support endurance training"
                        ],
  "potential_obstacles":"Inconsistent training schedules, risk of injury, lack of motivation on some days",
  "resources_needed":   "Running shoes, fitness tracker, access to a running track or outdoor space, a coach or training buddy for accountability",
  "start_date":         "2025-07-01",
  "end_date":           "2025-08-30"
}
                           """)
        print(result)
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
    # print(break_down_goal("write a book about my life"))

    # break down goal
    # goal json --> calendar events
    # goal json and calendar events --> reminder agent
    # reminder agent --> send email