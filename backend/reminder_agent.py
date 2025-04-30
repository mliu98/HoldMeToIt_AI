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
import time

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
SYSTEM_PROMPT = """You are a reminder generation assistant. Your task is to create reminders for calendar events based on the user's learning objectives and tasks.

IMPORTANT: Your response must be a valid, complete JSON object with the following structure:
{
    "event_reminders": [
        {
            "event_id": "string",  // Unique identifier for the event
            "reminders": [
                {
                    "datetime": "YYYY-MM-DD HH:mm",  // When to send the reminder
                    "message": "string",  // The reminder message
                    "priority": number,  // 1-10, where 10 is highest priority
                    "phase": "string"  // "preparation", "execution", or "follow_up"
                }
            ]
        }
    ]
}

Keep your response concise and focused on generating the JSON. Do not include any explanatory text outside the JSON block.
Ensure all JSON is properly formatted and complete. Do not use ellipsis (...) or truncate the JSON.
Each reminder should be actionable and specific to the event and learning objectives.

Remember:
1. All dates must be in "YYYY-MM-DD HH:mm" format
2. Priority must be between 1 and 10
3. Phase must be one of: "preparation", "execution", "follow_up"
4. Each event must have at least one reminder
5. Messages should be clear and actionable
"""

class ReminderTool:
    def __init__(self, client):
        self.client = client
        self.post_event_emails = {}
        logger.info("Reminder tool initialized")
    
    def generate_reminders_for_calendar_events(self, objective: Dict[str, Any], task_data: Dict[str, Any], calendar_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate reminders for calendar events"""
        try:
            # Format calendar events for the prompt
            events_text = "\n".join([
                f"{event['start']} - {event['summary']}"
                for event in calendar_events
            ])
            
            # Create a more structured prompt
            prompt = f"""Given these calendar events:
{events_text}

And this learning objective:
{json.dumps(objective, indent=2)}

And these tasks:
{json.dumps(task_data, indent=2)}

Generate a complete reminder schedule that helps achieve the objective while considering the calendar events.
Your response must be ONLY the JSON object, with no additional text or explanation.
Do not use markdown code blocks. Just return the raw JSON object.
Do not truncate or use ellipsis. Each reminder must be complete.

The response must be a valid JSON object with this structure:
{{
    "event_reminders": [
        {{
            "event_id": "string",  // Unique identifier for the event
            "reminders": [
                {{
                    "datetime": "YYYY-MM-DD HH:mm",  // When to send the reminder
                    "message": "string",  // The reminder message
                    "priority": number,  // 1-10, where 10 is highest priority
                    "phase": "string"  // "preparation", "execution", or "follow_up"
                }}
            ]
        }}
    ]
}}"""

            # Get response from LLM with increased max tokens
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                temperature=0.7,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            if response.content and len(response.content) > 0:
                response_text = response.content[0].text
                logger.debug(f"Raw LLM response: {response_text}")
                
                # Try to extract JSON
                data = self.extract_json_from_text(response_text)
                if data:
                    # Process reminders
                    successful_reminders = 0
                    successful_emails = 0
                    
                    for event_reminder in data["event_reminders"]:
                        try:
                            event_id = event_reminder["event_id"]
                            
                            # Process each reminder
                            for reminder in event_reminder["reminders"]:
                                try:
                                    # Parse datetime
                                    scheduled_time = datetime.datetime.strptime(reminder["datetime"], "%Y-%m-%d %H:%M")
                                    
                                    # Store in memory
                                    self.post_event_emails[event_id] = {
                                        "event_id": event_id,
                                        "subject": reminder.get("subject", f"Reminder: {event_id}"),
                                        "message": reminder["message"],
                                        "send_time": scheduled_time,
                                        "status": "pending"
                                    }
                                    successful_emails += 1
                                except Exception as e:
                                    logger.warning(f"Error processing reminder: {str(e)}")
                                    continue
                        except Exception as e:
                            logger.warning(f"Error processing event reminder: {str(e)}")
                            continue
                    
                    if not self.post_event_emails:
                        return {"success": False, "message": "No valid post-event emails were created"}
                    
                    return {
                        "success": True,
                        "message": f"Created {successful_emails} post-event emails",
                        "details": {
                            "total_events": len(data["event_reminders"]),
                            "successful_emails": successful_emails
                        }
                    }
                
                # If extraction failed, log the error
                logger.error(f"Failed to extract JSON from response: {response_text[:200]}...")
                return {"success": False, "message": "Failed to extract JSON from LLM response"}
            
            logger.error("Empty response from LLM")
            return {"success": False, "message": "Empty response from LLM"}
        except Exception as e:
            logger.error(f"Error generating calendar event reminders: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def process_pending_reminders(self) -> Dict[str, Any]:
        """Process and send due reminders"""
        try:
            now = datetime.datetime.now()
            
            # Find pending reminders that are due
            due_reminders = [
                e for e in self.post_event_emails.values() 
                if e["send_time"] <= now and e["status"] == "pending"
            ]
            
            if not due_reminders:
                return {"success": True, "message": "No pending reminders", "count": 0}
            
            sent_count = 0
            failed_count = 0
            
            for email in due_reminders:
                # Send email
                sent = self.send_reminder_email(
                    "user@example.com",  # Replace with actual email
                    email["message"],
                    email["subject"],
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
            logger.error(f"Error processing reminders: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def process_pending_post_event_emails(self) -> Dict[str, Any]:
        """Process and send pending post-event emails"""
        try:
            now = datetime.datetime.now()
            
            # Find pending post-event emails that are due
            due_emails = [
                e for e in self.post_event_emails.values() 
                if e["send_time"] <= now and e["status"] == "pending"
            ]
            
            if not due_emails:
                return {"success": True, "message": "No pending post-event emails", "count": 0}
            
            sent_count = 0
            failed_count = 0
            
            for email in due_emails:
                # Send email
                sent = self.send_reminder_email(
                    "user@example.com",  # Replace with actual email
                    email["message"],
                    email["subject"],
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
    
    def get_all_post_event_emails(self) -> List[Dict[str, Any]]:
        """Get all post-event emails"""
        return list(self.post_event_emails.values())

    def get_all_reminders(self) -> List[Dict[str, Any]]:
        """Get all reminders"""
        reminders = []
        for email in self.post_event_emails.values():
            if email["status"] == "pending":
                reminders.append({
                    "event_id": email["event_id"],
                    "message": email["message"],
                    "send_time": email["send_time"],
                    "subject": email["subject"]
                })
        return reminders

    def generate_reminders(self, objective: Dict[str, Any], calendar_events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate reminders based on objective and calendar events"""
        try:
            # Format calendar events for the prompt
            events_text = "\n".join([
                f"{event['start']} - {event['summary']}"
                for event in calendar_events
            ])
            
            # Create a more structured prompt
            prompt = f"""Given these calendar events:
{events_text}

And this learning objective:
{json.dumps(objective, indent=2)}

Generate a complete reminder schedule that helps achieve the objective while considering the calendar events.
Your response must be ONLY the JSON object, with no additional text or explanation.
Do not use markdown code blocks. Just return the raw JSON object.
Do not truncate or use ellipsis. Each reminder must be complete."""

            # Get response from LLM with increased max tokens
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                temperature=0.7,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            if response.content and len(response.content) > 0:
                response_text = response.content[0].text
                logger.debug(f"Raw LLM response: {response_text}")
                
                # Try to extract JSON
                data = self.extract_json_from_text(response_text)
                if data:
                    return data
                
                # If extraction failed, try to fix common issues
                cleaned_text = response_text.strip()
                if cleaned_text.startswith('```json'):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith('```'):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()
                
                try:
                    data = json.loads(cleaned_text)
                    if self.validate_reminder_data(data):
                        return data
                except json.JSONDecodeError:
                    pass
                
                # If still no valid JSON, log the error
                logger.error(f"Failed to extract JSON from response: {response_text[:200]}...")
                return None
            
            logger.error("Empty response from LLM")
            return None
        except Exception as e:
            logger.error(f"Error generating reminders: {str(e)}")
            return None

    def extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text"""
        try:
            # First try to find JSON in code blocks
            json_start = text.find("```json")
            if json_start != -1:
                json_start += 7  # Skip ```json
                json_end = text.find("```", json_start)
                if json_end != -1:
                    json_text = text[json_start:json_end].strip()
                    try:
                        data = json.loads(json_text)
                        if self.validate_reminder_data(data):
                            return data
                        else:
                            logger.error("Extracted JSON failed validation")
                            return None
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error in code block: {str(e)}")
                        return None
            
            # If no code block, try to find standalone JSON
            json_start = text.find("{")
            if json_start != -1:
                # Find the last complete object in the JSON
                stack = []
                in_string = False
                escape_next = False
                last_complete_end = -1
                
                for i in range(json_start, len(text)):
                    char = text[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                        
                    if char == '\\':
                        escape_next = True
                        continue
                        
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                        
                    if not in_string:
                        if char == '{':
                            stack.append(i)
                        elif char == '}':
                            if stack:
                                stack.pop()
                                if not stack:  # Found a complete object
                                    last_complete_end = i
                
                if last_complete_end != -1:
                    json_text = text[json_start:last_complete_end + 1].strip()
                    try:
                        data = json.loads(json_text)
                        if self.validate_reminder_data(data):
                            return data
                        else:
                            logger.error("Extracted JSON failed validation")
                            return None
                    except json.JSONDecodeError:
                        # If the JSON is incomplete, try to fix common issues
                        json_text = json_text.replace('\n', ' ').replace('\r', '')
                        json_text = json_text.replace('...', '')  # Remove ellipsis
                        json_text = json_text.replace('  ', ' ')  # Remove double spaces
                        try:
                            data = json.loads(json_text)
                            if self.validate_reminder_data(data):
                                return data
                            else:
                                logger.error("Extracted JSON failed validation after cleanup")
                                return None
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error after cleanup: {str(e)}")
                            return None
            
            # If still no JSON found, try to extract just the event_reminders array
            event_reminders_start = text.find('"event_reminders":')
            if event_reminders_start != -1:
                # Find the start of the array
                array_start = text.find('[', event_reminders_start)
                if array_start != -1:
                    # Find the matching closing bracket
                    stack = []
                    in_string = False
                    escape_next = False
                    
                    for i in range(array_start, len(text)):
                        char = text[i]
                        
                        if escape_next:
                            escape_next = False
                            continue
                            
                        if char == '\\':
                            escape_next = True
                            continue
                            
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                            
                        if not in_string:
                            if char == '[':
                                stack.append(i)
                            elif char == ']':
                                if stack:
                                    stack.pop()
                                    if not stack:  # Found the matching closing bracket
                                        json_text = text[array_start:i+1].strip()
                                        try:
                                            data = {"event_reminders": json.loads(json_text)}
                                            if self.validate_reminder_data(data):
                                                return data
                                            else:
                                                logger.error("Extracted event_reminders failed validation")
                                                return None
                                        except json.JSONDecodeError:
                                            # Try to fix common issues
                                            json_text = json_text.replace('\n', ' ').replace('\r', '')
                                            json_text = json_text.replace('...', '')
                                            json_text = json_text.replace('  ', ' ')
                                            try:
                                                data = {"event_reminders": json.loads(json_text)}
                                                if self.validate_reminder_data(data):
                                                    return data
                                                else:
                                                    logger.error("Extracted event_reminders failed validation after cleanup")
                                                    return None
                                            except json.JSONDecodeError as e:
                                                logger.error(f"JSON decode error after cleanup: {str(e)}")
                                                return None
            
            logger.error("No valid JSON found in response")
            return None
        except Exception as e:
            logger.error(f"Error extracting JSON: {str(e)}")
            return None

    def validate_reminder_data(self, data: Dict[str, Any]) -> bool:
        """Validate reminder data structure"""
        try:
            if not isinstance(data, dict):
                logger.error("Data is not a dictionary")
                return False
            
            if "event_reminders" not in data:
                logger.error("Missing event_reminders key")
                return False
            
            if not isinstance(data["event_reminders"], list):
                logger.error("event_reminders is not a list")
                return False
            
            for event in data["event_reminders"]:
                if not isinstance(event, dict):
                    logger.error("Event is not a dictionary")
                    return False
                
                if "event_id" not in event:
                    logger.error("Missing event_id")
                    return False
                
                if "reminders" not in event:
                    logger.error("Missing reminders")
                    return False
                
                if not isinstance(event["reminders"], list):
                    logger.error("Reminders is not a list")
                    return False
                
                for reminder in event["reminders"]:
                    if not isinstance(reminder, dict):
                        logger.error("Reminder is not a dictionary")
                        return False
                    
                    required_fields = ["datetime", "message", "priority", "phase"]
                    for field in required_fields:
                        if field not in reminder:
                            logger.error(f"Missing {field} in reminder")
                            return False
                    
                    if not isinstance(reminder["priority"], (int, float)):
                        logger.error("Priority is not a number")
                        return False
                    
                    if not (1 <= reminder["priority"] <= 10):
                        logger.error("Priority must be between 1 and 10")
                        return False
                    
                    if not isinstance(reminder["phase"], str):
                        logger.error("Phase is not a string")
                        return False
                    
                    valid_phases = ["preparation", "execution", "follow_up"]
                    if reminder["phase"] not in valid_phases:
                        logger.error(f"Invalid phase: {reminder['phase']}")
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating reminder data: {str(e)}")
            return False

def send_reminder_email(email: str, message: str, subject: str, phase: str, msg_id: str = None, references: str = None) -> bool:
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