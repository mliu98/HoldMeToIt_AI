import os
import json
import asyncio
import datetime
import uuid
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import requests
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("reminder_tool.log"), logging.StreamHandler()]
)
logger = logging.getLogger("mcp_reminder_tool")

# Load environment variables
load_dotenv()

# System prompt for the LLM
SYSTEM_PROMPT = """
You are an intelligent reminder scheduler for goals and tasks. Your job is to analyze a user's objective and task breakdown to create optimal reminder schedules that align with both.

You will receive two JSON objects:
1. The user's high-level objective with context, constraints, and deadlines
2. A detailed task breakdown with specific dates, dependencies, and milestones

Create a schedule of reminders that will help the user achieve their goal by connecting reminders to specific tasks, phases of work, and the overall objective. Reminders should be timed based on:
- Task start and end dates
- Task dependencies and transitions
- Milestone achievements
- The overall objective deadline

For each task, create reminders that:
1. Align with specific milestones in the task
2. Provide guidance for achieving each milestone
3. Check progress towards milestone completion
4. Celebrate milestone achievements

Each reminder should include:
- A specific datetime (formatted as ISO-8601)
- A helpful message relevant to the current task/phase/milestone
- The related task title
- The specific milestone it relates to (if applicable)
- A priority level (1-10)
- A phase indicator (preparation, execution, completion, transition)

Return a JSON object with the following structure:
{
  "reminders": [
    {
      "datetime": "2025-04-28T09:00:00",
      "message": "Start your baseline fitness assessment today. Measure your current 1-mile time and record your heart rate.",
      "related_task": "Establish Baseline Fitness",
      "related_milestone": "Complete 1-mile timed assessment",
      "priority": 7,
      "phase": "preparation"
    },
    // Additional reminders...
  ]
}
"""

class ReminderTool:
    def __init__(self):
        """Initialize in-memory storage"""
        self.reminders = []
        self.post_event_emails = []
        logger.info("Reminder tool initialized")
    
    async def generate_reminders_for_calendar_events(self, objective_data: Dict[str, Any], task_data: Dict[str, Any], calendar_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate reminders for calendar events using LLM"""
        try:
            # Set up Claude API request
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return {"success": False, "message": "Missing LLM API key"}
            
            # Format input data
            input_json = json.dumps({
                "objective": objective_data,
                "task_breakdown": task_data,
                "calendar_events": calendar_events
            }, indent=2)
            
            # Create system prompt for calendar event reminders
            calendar_prompt = """
            You are an intelligent reminder scheduler that determines the optimal times to send reminders for calendar events.
            
            Analyze the following information to determine the best reminder schedule:
            1. Calendar event details (time, duration, type)
            2. Related task and milestone
            3. User's work schedule and preferences
            4. Event preparation needs
            5. Post-event follow-up requirements
            
            For each calendar event, determine:
            1. How many reminders are needed before the event
            2. When each reminder should be sent
            3. The optimal time of day for each reminder
            4. A motivational message to send after the event
            
            Consider:
            - Event type and importance
            - Preparation time needed
            - User's schedule and preferences
            - Natural breaks in the day
            - Post-event reflection and motivation
            
            Return a JSON object with the following structure:
            {
                "event_reminders": [
                    {
                        "event_id": "event_123",
                        "reminders": [
                            {
                                "datetime": "YYYY-MM-DD HH:MM",
                                "message": "Reminder message",
                                "priority": 1-10,
                                "phase": "preparation/execution"
                            }
                        ],
                        "post_event_email": {
                            "subject": "Email subject",
                            "message": "Motivational message",
                            "send_time": "YYYY-MM-DD HH:MM"
                        }
                    }
                ]
            }
            """
            
            # Make API request to Claude
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            payload = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 4000,
                "system": calendar_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Please analyze these calendar events and create an optimal reminder schedule:\n\n{input_json}"
                    }
                ]
            }
            
            # Add retry logic for API calls
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        "https://api.anthropic.com/v1/messages",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        break
                    elif response.status_code == 502 and attempt < max_retries - 1:
                        logger.warning(f"API error 502, retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return {"success": False, "message": f"LLM API error: {response.status_code}"}
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"API request failed, retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise e
            
            # Extract and parse response
            response_data = response.json()
            response_text = response_data.get("content", [{}])[0].get("text", "")
            
            # Extract JSON from response
            reminders_data = extract_json_from_text(response_text)
            
            if not reminders_data or "event_reminders" not in reminders_data:
                return {"success": False, "message": "Failed to parse valid reminders from LLM response"}
            
            # Store reminders and schedule post-event emails
            for event_reminder in reminders_data["event_reminders"]:
                event_id = event_reminder["event_id"]
                
                # Store reminders
                for reminder in event_reminder["reminders"]:
                    reminder_id = f"rem_{uuid.uuid4().hex[:8]}"
                    scheduled_time = datetime.datetime.strptime(reminder["datetime"], "%Y-%m-%d %H:%M")
                    
                    # Store in memory
                    self.reminders.append({
                        "id": reminder_id,
                        "message": reminder["message"],
                        "scheduled_time": scheduled_time,
                        "status": "pending",
                        "related_task": event_id,
                        "priority": reminder["priority"],
                        "phase": reminder["phase"],
                        "email": "user@example.com"  # Replace with actual email
                    })
                
                # Schedule post-event email
                post_event = event_reminder["post_event_email"]
                send_time = datetime.datetime.strptime(post_event["send_time"], "%Y-%m-%d %H:%M")
                
                # Store post-event email
                self.post_event_emails.append({
                    "event_id": event_id,
                    "subject": post_event["subject"],
                    "message": post_event["message"],
                    "send_time": send_time,
                    "status": "pending"
                })
            
            return {
                "success": True,
                "message": f"Created reminders and scheduled post-event emails for {len(reminders_data['event_reminders'])} events"
            }
            
        except Exception as e:
            logger.error(f"Error generating calendar event reminders: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def process_pending_reminders(self) -> Dict[str, Any]:
        """Process and send due reminders"""
        try:
            now = datetime.datetime.now()
            
            # Find pending reminders that are due
            due_reminders = [
                r for r in self.reminders 
                if r["scheduled_time"] <= now and r["status"] == "pending"
            ]
            
            if not due_reminders:
                return {"success": True, "message": "No pending reminders", "count": 0}
            
            sent_count = 0
            failed_count = 0
            
            for reminder in due_reminders:
                # Send email
                sent = await send_reminder_email(
                    reminder["email"],
                    reminder["message"],
                    reminder.get("subject", f"Reminder: {reminder['related_task']}"),  # Use reminder's subject if available
                    reminder["phase"],
                    msg_id=None,
                    references=None
                )
                
                if sent:
                    # Mark as sent
                    reminder["status"] = "sent"
                    reminder["sent_at"] = now
                    sent_count += 1
                else:
                    failed_count += 1
            
            return {
                "success": True,
                "message": f"Processed {sent_count} reminders ({failed_count} failed)",
                "count": sent_count
            }
            
        except Exception as e:
            logger.error(f"Error processing reminders: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def process_pending_post_event_emails(self) -> Dict[str, Any]:
        """Process and send pending post-event emails"""
        try:
            now = datetime.datetime.now()
            
            # Find pending post-event emails that are due
            due_emails = [
                e for e in self.post_event_emails 
                if e["send_time"] <= now and e["status"] == "pending"
            ]
            
            if not due_emails:
                return {"success": True, "message": "No pending post-event emails", "count": 0}
            
            sent_count = 0
            failed_count = 0
            
            for email in due_emails:
                # Send email
                sent = await send_reminder_email(
                    "user@example.com",  # Replace with actual email
                    email["message"],
                    f"Post-Event: {email['event_id']}",
                    "completion",
                    msg_id=None,
                    references=None
                )
                
                if sent:
                    # Mark as sent
                    email["status"] = "sent"
                    email["sent_at"] = now
                    sent_count += 1
                else:
                    failed_count += 1
            
            return {
                "success": True,
                "message": f"Processed {sent_count} post-event emails ({failed_count} failed)",
                "count": sent_count
            }
            
        except Exception as e:
            logger.error(f"Error processing post-event emails: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def get_all_reminders(self) -> List[Dict[str, Any]]:
        """Get all reminders"""
        return self.reminders
    
    def get_all_post_event_emails(self) -> List[Dict[str, Any]]:
        """Get all post-event emails"""
        return self.post_event_emails

async def send_reminder_email(email: str, message: str, subject: str, phase: str, msg_id: str = None, references: str = None) -> bool:
    """Send reminder email"""
    if not email:
        return False
    
    try:
        # Get email credentials
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")
        email_server = os.getenv("EMAIL_SERVER", "smtp.mail.yahoo.com")
        email_port = int(os.getenv("EMAIL_PORT", "587"))
        
        if not email_user or not email_password:
            logger.error("Missing email credentials")
            return False
        
        # Create email
        msg = EmailMessage()
        
        # Set plain text content
        msg.set_content(message)
        
        # Set headers
        msg["Subject"] = subject
        msg["From"] = email_user
        msg["To"] = email
        
        # Set message ID and threading headers
        if msg_id:
            msg["Message-ID"] = msg_id
        if references:
            msg["References"] = references
        else:
            # Ensure no threading happens
            msg["Thread-Index"] = make_msgid(domain="no-threading")
        
        # Send email
        try:
            server = smtplib.SMTP(email_server, email_port)
            server.starttls()
            server.login(email_user, email_password)
            server.send_message(msg)
            server.quit()
            logger.info(f"Sent reminder to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from response text"""
    try:
        # Look for JSON blocks
        json_start = text.find("```json")
        if json_start != -1:
            json_start += 7  # Skip ```json
            json_end = text.find("```", json_start)
            if json_end != -1:
                json_text = text[json_start:json_end].strip()
                return json.loads(json_text)
        
        # Try to find standalone JSON
        json_start = text.find("{")
        if json_start != -1:
            json_end = text.rfind("}")
            if json_end != -1 and json_end > json_start:
                json_text = text[json_start:json_end + 1].strip()
                return json.loads(json_text)
        
        return None
    except json.JSONDecodeError:
        return None