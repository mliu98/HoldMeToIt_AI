from typing import Any, List, Dict
import httpx
from mcp.server.fastmcp import FastMCP
import json
from datetime import datetime, timedelta
import anthropic
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from reminder_agent import send_reminder_email
import os
import sys
import logging
import pickle

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


    
def create_calendar_event(summary, start_time, end_time, description=None, location=None, attendees=None, timezone='UTC'):
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 
              'https://www.googleapis.com/auth/calendar.events.owned']
    """
    Based on the given summary, start_time, end_time, call google calendar api and create event there.
    Parameters:
    - summary: String, title of the event
    - start_time: Datetime object or ISO format string for event start
    - end_time: Datetime object or ISO format string for event end
    - description: String, description of the event (optional)
    - location: String, location of the event (optional)
    - attendees: List of dictionaries with email addresses (optional)
    - timezone: String, timezone for the event (default: 'UTC')
    """
    # Get credentials
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES + ['https://www.googleapis.com/auth/calendar.events'])
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    service = build('calendar', 'v3', credentials=creds)
    
    # Convert datetime objects to RFC3339 timestamp if needed
    if isinstance(start_time, datetime):
        start_time = start_time.isoformat() + 'Z'
    if isinstance(end_time, datetime):
        end_time = end_time.isoformat()  + 'Z'
    
    # Create event body
    event_body = {
        'summary': summary,
        'start': {
            'dateTime': start_time,
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': timezone,
        }
    }
    
    # Add optional fields if provided
    if description:
        event_body['description'] = description
    if location:
        event_body['location'] = location
    if attendees:
        event_body['attendees'] = attendees
    
    # Add default reminders
    event_body['reminders'] = {
        'useDefault': True
    }
    
    # Create the event
    try:
        # Call the Calendar API
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        one_week_later = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

        print("\nNOW: ", now)
        print("ONE_WEEK_LATER: ", one_week_later)

        print("\nSTART_TIME: ", start_time)
        print("END_TIME: ", end_time, "\n")
        
        existing_events = service.events().list(
            calendarId='primary',
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        if existing_events.get('items'):
            print(f"Event not created: There are {len(existing_events['items'])} existing events during this time period")
            return json.dumps({
                "status": "error",
                "message": f"There are {len(existing_events['items'])} existing events during this time period"
            })
        else:
            event = service.events().insert(calendarId='primary', body=event_body).execute()
            print(f"Event created: {event.get('htmlLink')}")
            return json.dumps({
                "status": "success",
                "event_link": event.get('htmlLink'),
                "event_id": event.get('id')
            })
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        })

@mcp.tool()
def send_email(scheduled_tasks):
    """
    Take in subtasks/break down tasks: goal_json from tool <scheduled_tasks>, 
     [{{
            "TaskName": "Phase Name - Task Name",
            "StartDateTime": "2025-05-03 07:00",
            "EndDateTime": "2025-05-03 08:00",
            "Description": "Detailed description of the task"
        }}, ... ]
    """

    instruction = f"""
    Please format the scheduled_tasks in a proper plan format that can be display in a email body: {scheduled_tasks}
    """

    response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=5000,
            temperature=0.7,
            system="You are a email assistant, that your job is to format the given content into a format that can sent in a google email. Please only return the email body without anything else.",
            messages=[
                {
                    "role": "user",
                    "content": instruction
                }
            ]
        )
        
    # Get the response text and clean it
    response_text = response.content[0].text.strip()
    print("LLM Response:", response_text)

    full_message = response_text
    try:
        sent = send_reminder_email(email="ai.goals.coach@gmail.com",  
                                   subject="🎯Goal Assistant - Your plan is ready!", 
                                   message=full_message,
                                   phase="completion",
                                   msg_id=None,
                                   references=None
        )
        if sent:
            return f"Successfully sent email."
    except Exception as e:
        return f"Failed sending the email. {e}"

    

@mcp.tool()
def schedule_goal_tasks(goal_json):
    """Take in subtasks/break down tasks: goal_json from tool <break_down_goal>, and has the following format
{
  "goal": main goal,
  "deadline": give a rough estimation of the date the goal should be done,
  "start_date": "When work on the goal begins",
  "end_date":  "Deadline for goal completion"
  "timelineTasks": [
    {
        id: 1,
        text: "Phase I",
        date: "April 19-21",
        subtasks: [
            {id: 1, text: "Define project scope and requirements", completed: true},
            {id: 2, text: "Set up development environment", completed: true}
        ]
    },
    ...
  ]
}
        for each tasks, find a suitable time frame from today and convert the task timeframe
        into utc time, create the google calendar event. If events are created successfully, output all the successful event. """

    print("Scheduling goal tasks...")
    
    try:
        # Parse the goal JSON if it's a string
        if isinstance(goal_json, str):
            goal_json = json.loads(goal_json)
        
        # Extract goal information
        goal = goal_json.get('goal', '')
        start_date = goal_json.get('start_date', '')
        end_date = goal_json.get('end_date', '')
        
        # Collect all subtasks from timeline tasks
        all_subtasks = []
        for phase in goal_json.get('timelineTasks', []):
            for subtask in phase.get('subtasks', []):
                all_subtasks.append({
                    'phase': phase.get('text', ''),
                    'task': subtask.get('text', ''),
                    'completed': subtask.get('completed', False)
                })
        
        # Prepare instruction for LLM
        instruction = f"""
        Break down the following goal into scheduled subtasks:
        Goal: {goal}
        Overall timeframe: {start_date} to {end_date}
        Subtasks to schedule: {', '.join([f"{st['phase']} - {st['task']}" for st in all_subtasks])}
        
        For each subtask, provide:
        1. Start date and time
        2. End date and time
        3. Brief description
        
        Format each task as: 
        [{{
            "TaskName": "Phase Name - Task Name",
            "StartDateTime": "2025-05-03 07:00",
            "EndDateTime": "2025-05-03 08:00",
            "Description": "Detailed description of the task"
        }}, ... ]
        Use 24-hour time format (YYYY-MM-DD HH:MM)
        Ensure all times fall within the overall timeframe.
        Space out the tasks evenly across the available time period.
        Make sure each task has enough time to be completed.

        Only return the above json, remove any markdown format
        """
        
        # Get response from Claude
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=0.7,
            system="You are a calendar assistant. You are given a goal and you need to break it down into subtasks and schedule them as calendar events.",
            messages=[
                {
                    "role": "user",
                    "content": instruction
                }
            ]
        )
        
        # Get the response text and clean it
        response_text = response.content[0].text.strip()
        print("LLM Response:", response_text)
        
        # Parse the scheduled tasks
        scheduled_tasks = json.loads(response_text)
        scheduled_events = []
        
        # Schedule each task
        for task in scheduled_tasks:
            try:
                task_start = datetime.strptime(task['StartDateTime'].strip(), '%Y-%m-%d %H:%M')
                task_end = datetime.strptime(task['EndDateTime'].strip(), '%Y-%m-%d %H:%M')
                
                # Create calendar event
                event_result = create_calendar_event(
                    summary=task['TaskName'],
                    start_time=task_start,
                    end_time=task_end,
                    description=task['Description'],
                    timezone='UTC'
                )
                
                # Parse the event result
                event_data = json.loads(event_result)
                if event_data.get('status') == 'success':
                    scheduled_events.append(event_data)
                else:
                    print(f"Failed to schedule task {task['TaskName']}: {event_data.get('message')}")
            
            except Exception as e:
                print(f"Error processing task {task.get('TaskName', 'unknown')}: {str(e)}")
                continue
        
        # Return the results
        if scheduled_events:
            print(json.dumps({
                "status": "success",
                "message": f"Successfully scheduled {len(scheduled_events)} tasks",
                "events": scheduled_events
            }))
            return json.dumps(scheduled_tasks)
        else:
            return json.dumps({
                "status": "error",
                "message": "No tasks were successfully scheduled"
            })
    
    except Exception as e:
        print(f"Error scheduling tasks: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Error scheduling tasks: {str(e)}"
        })




@mcp.tool()
def break_down_goal(goal: str) -> str:
    """Summarize user's input. Break down the input into tasks and generate a timeline.
    
    Args:
        goal: A object / goal that user input for breaking down into subtasks.
    Output: 
        subtasks: A json array that contains all the breakdown tasks
    """
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Use Claude to break down the goal
        system_prompt = """
You are a compassionate, insightful Goal Achievement Coach with expertise in personal development and behavioral psychology. 
Return the subtasks as the following json format. Should not be more than 3 phases and 6 subtasks:
{{
  "goal": main goal,
  "deadline": give a rough estimation of the date the goal should be done based on current date {current_date} as format 2025-05-01,
  "start_date": When work on the goal begins need to provide a specific date as format 2025-05-01,
  "end_date":  Deadline for goal completion need to provide a specific date as format 2025-05-01
  "timelineTasks": [
    {{
        id: 1,
        text: "Phase I",
        date: "April 19-21",
        subtasks: [
            {{id: 1, text: "Define project scope and requirements", completed: true}},
            {{id: 2, text: "Set up development environment", completed: true}}
        ]
    }},
    ...
  ]
}}
""".format(current_date=current_date)


        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Break down this goal into specific tasks and return ONLY a JSON array. Do not return any other stuff only return a JSON as defined: {goal}. Remove any markdown format. Only plaintext json."
                }
            ]
        )
        
        # Get the response text and clean it
        response_text = response.content[0].text.strip()
        
        # Debug: Print the raw response
        print("Raw response:", response_text)
        return response_text
        
        
    except Exception as e:
        return f"Error breaking down goal: {str(e)}\nResponse text: {response_text if 'response_text' in locals() else 'No response'}"

if __name__ == "__main__":
    try:
        logger.info("Starting MCP server...")
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")
        sys.exit(1)
  
    # goal_json = break_down_goal("i want to run 5km in a week")
    # schedule_goal_tasks(goal_json)