import asyncio
import datetime
from email.utils import make_msgid
from typing import Dict, List, Any
import logging
from reminder_agent import send_reminder_email

logger = logging.getLogger(__name__)

class EmailScheduler:
    def __init__(self):
        """Initialize the email scheduler"""
        self.scheduled_tasks = []
        self.running = False

    async def schedule_email(self, 
                           email: str, 
                           subject: str, 
                           message: str, 
                           send_time: datetime.datetime,
                           event_details: Dict[str, Any] = None) -> None:
        """Schedule an email to be sent at a specific time"""
        now = datetime.datetime.now()
        
        # If the send time is in the past, don't schedule
        if send_time <= now:
            logger.warning(f"Send time {send_time} is in the past, skipping scheduling")
            return

        # Calculate wait time
        wait_seconds = (send_time - now).total_seconds()
        logger.info(f"Scheduling email '{subject}' to be sent in {wait_seconds/3600:.1f} hours")

        # Create the email task
        async def send_email_task():
            try:
                # Wait until it's time to send
                await asyncio.sleep(wait_seconds)
                
                # Generate unique message ID
                msg_id = make_msgid(domain="reminder.local")
                
                # Format the message with event details if provided
                full_message = message
                if event_details:
                    full_message = f"""Event Details:
Title: {event_details.get('title', 'N/A')}
Time: {event_details.get('start_time', 'N/A')} - {event_details.get('end_time', 'N/A')}
Location: {event_details.get('location', 'N/A')}
Description: {event_details.get('description', 'N/A')}
Related Milestone: {event_details.get('related_milestone', 'N/A')}
Preparation Needs: {', '.join(event_details.get('preparation_needs', []))}

{message}"""

                # Send the email
                sent = await send_reminder_email(
                    email,
                    full_message,
                    subject,
                    "reminder",
                    msg_id=msg_id,
                    references=None
                )
                
                if sent:
                    logger.info(f"Successfully sent email '{subject}' at {datetime.datetime.now()}")
                else:
                    logger.error(f"Failed to send email '{subject}'")
                    
            except Exception as e:
                logger.error(f"Error sending scheduled email: {str(e)}")

        # Add the task to our list
        task = asyncio.create_task(send_email_task())
        self.scheduled_tasks.append(task)

    async def schedule_reminders(self, 
                               reminders: List[Dict[str, Any]], 
                               events: List[Dict[str, Any]]) -> None:
        """Schedule multiple reminders"""
        for reminder in reminders:
            # Find corresponding event
            event = next((e for e in events if e["event_id"] == reminder["related_task"]), None)
            if event:
                await self.schedule_email(
                    email=reminder["email"],
                    subject=reminder.get("subject", f"Reminder: {event['title']} - {reminder['phase'].title()}"),
                    message=reminder["message"],
                    send_time=reminder["scheduled_time"],
                    event_details=event
                )

    async def schedule_post_event_emails(self, 
                                       emails: List[Dict[str, Any]], 
                                       events: List[Dict[str, Any]]) -> None:
        """Schedule multiple post-event emails"""
        for email in emails:
            # Find corresponding event
            event = next((e for e in events if e["event_id"] == email["event_id"]), None)
            if event:
                await self.schedule_email(
                    email=email["email"],
                    subject=email["subject"],
                    message=email["message"],
                    send_time=email["send_time"],
                    event_details=event
                )

    async def wait_for_completion(self) -> None:
        """Wait for all scheduled tasks to complete"""
        if self.scheduled_tasks:
            await asyncio.gather(*self.scheduled_tasks)
            self.scheduled_tasks = [] 