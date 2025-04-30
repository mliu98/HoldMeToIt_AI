import datetime
import json
import os
from anthropic import Anthropic
from reminder_agent import ReminderTool
from email_scheduler import EmailScheduler
from calendar_functions import get_calendar_events, get_calendar_events_json

def test_knitting_reminders():
    # Initialize Anthropic client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    client = Anthropic(api_key=api_key)

    # Example objective data
    objective_data = {
        "primary_objective": "Learn to knit and complete a simple project",
        "success_criteria": [
            "Master basic knitting stitches",
            "Complete a simple scarf project",
            "Understand knitting terminology and patterns"
        ],
        "timeline": {
            "deadline": "2025-05-25",
            "critical_dates": [
                {"date": "2025-05-25", "reason": "Project completion deadline"},
                {"date": "2025-05-11", "reason": "Mid-project check-in"},
                {"date": "2025-04-27", "reason": "Start of learning journey"}
            ]
        },
        "resources": {
            "available": [
                "Knitting needles",
                "Yarn",
                "Online tutorials",
                "Weekend practice time",
                "Local knitting group"
            ],
            "constraints": [
                "Weekday evenings only",
                "Limited budget for materials",
                "No prior knitting experience"
            ]
        },
        "domain_context": "Complete beginner learning to knit",
        "dependencies": [
            "Basic knitting supplies",
            "Access to learning resources",
            "Regular practice time"
        ],
        "priority_level": "Medium - Personal hobby with specific deadline",
        "previous_attempts": "No prior knitting experience"
    }

    # Example task data
    task_data = {
        "goal": "I want to learn how to knit",
        "tasks": [
            {
                "title": "Learn Basic Knitting Techniques",
                "description": "Master the fundamental knitting stitches and techniques",
                "estimated_duration": "7 days",
                "dependencies": [],
                "milestones": [
                    "Learn to cast on",
                    "Master knit stitch",
                    "Master purl stitch",
                    "Learn to bind off"
                ],
                "start_date": "2025-04-27",
                "end_date": "2025-05-04"
            },
            {
                "title": "Practice Basic Patterns",
                "description": "Practice creating simple patterns and textures",
                "estimated_duration": "7 days",
                "dependencies": ["Learn Basic Knitting Techniques"],
                "milestones": [
                    "Create garter stitch swatch",
                    "Create stockinette stitch swatch",
                    "Practice ribbing pattern",
                    "Learn to read basic patterns"
                ],
                "start_date": "2025-05-05",
                "end_date": "2025-05-11"
            },
            {
                "title": "Start Scarf Project",
                "description": "Begin working on a simple scarf project",
                "estimated_duration": "14 days",
                "dependencies": ["Practice Basic Patterns"],
                "milestones": [
                    "Choose yarn and pattern",
                    "Cast on for scarf",
                    "Complete first 6 inches",
                    "Learn to fix common mistakes"
                ],
                "start_date": "2025-05-12",
                "end_date": "2025-05-25"
            }
        ]
    }

    # Get calendar events and convert to JSON
    events = get_calendar_events()
    calendar_events_json = get_calendar_events_json(events)
    
    # Parse the JSON back to a list of dictionaries
    calendar_events = json.loads(calendar_events_json)

    # Initialize the reminder tool and scheduler
    tool = ReminderTool(client)
    scheduler = EmailScheduler()
    
    # Generate reminders for calendar events
    result = tool.generate_reminders_for_calendar_events(objective_data, task_data, calendar_events)
    
    if result["success"]:
        print("\nGenerated Knitting Learning Reminders:")
        print("====================================")
        
        # Show post-event emails
        emails = tool.get_all_post_event_emails()
        print("\nPost-Event Emails:")
        print("----------------")
        for email in emails:
            # Find the corresponding calendar event
            event = next((e for e in calendar_events if e["summary"] == email["event_id"]), None)
            if event:
                print(f"\nEvent: {event['summary']}")
                print(f"Subject: {email['subject']}")
                print(f"Send Time: {email['send_time'].strftime('%Y-%m-%d %H:%M')}")
                print(f"Message: {email['message']}")
                print("-" * 50)
        
        print("\nScheduling Reminders and Emails:")
        print("===============================")
        
        # Update email addresses
        for email in emails:
            email["email"] = "galada108@yahoo.com"
        
        # Schedule all reminders and emails
        scheduler.schedule_post_event_emails(emails, calendar_events)
        
        # Wait for all scheduled tasks to complete
        scheduler.wait_for_completion()
        
    else:
        print(f"Error: {result['message']}")

if __name__ == "__main__":
    test_knitting_reminders() 