from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle

from typing import Any, List, Dict
import httpx
from mcp.server.fastmcp import FastMCP
import json
from datetime import datetime, timedelta
import anthropic
from dotenv import load_dotenv

# Initialize FastMCP server
#mcp = FastMCP("goal_tracker")
#load_dotenv()

import anthropic
client = anthropic.Anthropic()

def schedule_goal_tasks(goal_json):
    """ 
        Takes a goal JSON and schedules subtasks as calendar events.
        
        Expected goal_json format:
        {
            "goal_statement":     "Clear statement of the desired outcome",
            "success_metrics":    "How progress/completion will be measured",
            "importance_context": "Why this matters/motivation",
            "current_state":      "Assessment of starting point",
            "sub_tasks":          "Breakdown into actionable components",
            "potential_obstacles":"Anticipated challenges",
            "resources_needed":   "Tools, information, or support required",
            "start_date":         "When work on the goal begins",
            "end_date":           "Deadline for goal completion"
        }
    """

    print("Scheduling goal tasks...")
    
    # Convert date strings to datetime objects
    start_date = datetime.strptime(goal_json['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(goal_json['end_date'], '%Y-%m-%d')
    
    # Prepare instruction for LLM
    instruction = f"""
    Break down the following goal into scheduled subtasks:
    Goal: {goal_json['goal_statement']}
    Overall timeframe: {goal_json['start_date']} to {goal_json['end_date']}
    Subtasks to schedule: {', '.join(goal_json['sub_tasks'])}
    
    For each subtask, provide:
    1. Start date and time
    2. End date and time
    3. Brief description
    
    Format each task as: TaskName|StartDateTime|EndDateTime|Description
    Use 24-hour time format (YYYY-MM-DD HH:MM)
    Ensure all times fall within the overall timeframe.
    """
    
    try:
        # Get response from Claude
    
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=0.7,
            system=" You are a calendar assistant. You are given a goal and you need to break it down into subtasks and schedule them as calendar events.",
            messages=[
                {
                    "role": "user",
                    "content": instruction
                }
            ]
        )
        
        # Get the response text and clean it
        response_text = response.content[0].text.strip()

        
        # Parse the response
        tasks_raw = response.choices[0].message.content.strip().split('\n')
        
        # Schedule each task
        scheduled_events = []

        for task in tasks_raw:
            if not task or '|' not in task:
                continue
                
            name, start_str, end_str, desc = task.split('|')
            
            # Convert strings to datetime objects
            task_start = datetime.strptime(start_str.strip(), '%Y-%m-%d %H:%M')
            task_end = datetime.strptime(end_str.strip(), '%Y-%m-%d %H:%M')
            
            # Create calendar event
            event = create_calendar_event(
                summary=name.strip(),
                start_time=task_start,
                end_time=task_end,
                description=desc.strip(),
                timezone='UTC'
            )
            
            if event:
                scheduled_events.append(event)
        
        return scheduled_events
    
    except Exception as e:
        print(f"Error scheduling tasks: {e}")
        return None


def get_calendar_events():
    """Gets events from Google Calendar for the next week."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    one_week_later = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
    
    print('Getting events for the next week...')
    events_result = service.events().list(calendarId='primary', 
                                        timeMin=now,
                                        timeMax=one_week_later,
                                        singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        return []
    
    # Process and return the events
    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        
        # Format the start time
        if 'T' in start:  # This is a dateTime format
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            start_formatted = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:  # This is a date format (all-day event)
            start_formatted = start + " (All day)"
            
        formatted_events.append({
            'summary': event.get('summary', 'No title'),
            'start': start_formatted,
            'description': event.get('description', 'No description'),
            'location': event.get('location', 'No location')
        })
        
        print(f"{start_formatted} - {event.get('summary', 'No title')}")
    
    return formatted_events


def create_calendar_event(summary, start_time, end_time, description=None, location=None, attendees=None, timezone='UTC'):
    """
    Creates an event on Google Calendar
    
    Parameters:
    - summary: String, title of the event
    - start_time: Datetime object or ISO format string for event start
    - end_time: Datetime object or ISO format string for event end
    - description: String, description of the event (optional)
    - location: String, location of the event (optional)
    - attendees: List of dictionaries with email addresses (optional)
    - timezone: String, timezone for the event (default: 'UTC')
    
    Returns:
    - Created event object
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
            #timeMin=now,
            #timeMax=one_week_later,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        if existing_events.get('items'):
            print(f"Event not created: There are {len(existing_events['items'])} existing events during this time period")
            return None
        else:
            event = service.events().insert(calendarId='primary', body=event_body).execute()
            print(f"Event created: {event.get('htmlLink')}")
            return event
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    

def get_calendar_events_json(events):
    """Converts a list of calendar events to JSON format.
    
    Args:
        events: List of event dictionaries from get_calendar_events()
        
    Returns:
        JSON string containing the formatted events
    """
    return json.dumps(events)

if __name__ == '__main__':

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 
              'https://www.googleapis.com/auth/calendar.events.owned']
    
    example_goal = {
        "goal_statement":     "To run a 5k",
        "success_metrics":    "How progress/completion will be measured",
        "importance_context": "Why this matters/motivation",
        "current_state":      "Assessment of starting point",
        "sub_tasks":          "Short 30 minute runs",
        "potential_obstacles":"Anticipated challenges",
        "resources_needed":   "Tools, information, or support required",
        "start_date":         "2025-05-01",
        "end_date":           "2025-06-01"
        }
    
    # Initialize and run the server
    #mcp.run(transport='stdio')    
    schedule_goal_tasks(example_goal)
    
    ''' 
    events = get_calendar_events()
    print(f"Total events in the next week: {len(events)}")
    
    
    # Example: Create a meeting tomorrow from 2-3pm UTC
    tomorrow = datetime.utcnow() + timedelta(days=1)
    start = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
    end = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
    
    create_calendar_event(
        summary="Sample Meeting",
        start_time=start,
        end_time=end,
        description="Discuss project progress and next steps",
        location="Conference Room A",
        attendees=[
            {'email': 'colleague@example.com'},
            {'email': 'manager@example.com'}
        ],
        timezone='UTC'
    )
    

    events = get_calendar_events()
    print(f"\n\nUpdated total events in the next week: {len(events)}")

    '''