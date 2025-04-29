import random
import datetime
import time
import schedule
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables for email credentials
load_dotenv()

def create_reminder_agent(start_date, end_date, min_reminders, max_reminders, 
                          message, email_to, time_range=(8, 22)):
    """
    Creates an agent that sends random reminders within a date range.
    
    Parameters:
    - start_date: datetime.date - The first possible date for reminders
    - end_date: datetime.date - The last possible date for reminders
    - min_reminders: int - Minimum number of reminders to send
    - max_reminders: int - Maximum number of reminders to send
    - message: str - The reminder message to send
    - email_to: str - Recipient's email address
    - time_range: tuple - (start_hour, end_hour) to restrict when reminders can be sent
    
    Returns:
    - list of scheduled reminder times
    """
    # Validate input parameters
    if start_date > end_date:
        raise ValueError("Start date must be before end date")
    
    if min_reminders <= 0 or max_reminders <= 0:
        raise ValueError("Number of reminders must be positive")
    
    if min_reminders > max_reminders:
        raise ValueError("Minimum reminders cannot exceed maximum reminders")
    
    # Calculate total days in the range
    delta = end_date - start_date
    total_days = delta.days + 1
    
    if total_days <= 0:
        raise ValueError("Date range must include at least one day")
    
    # Determine number of reminders to send
    num_reminders = random.randint(min_reminders, max_reminders)
    
    # Generate random dates and times for reminders
    reminders = []
    for _ in range(num_reminders):
        # Pick a random day within the range
        random_day = random.randint(0, total_days - 1)
        reminder_date = start_date + datetime.timedelta(days=random_day)
        
        # Pick a random hour within the specified time range
        random_hour = random.randint(time_range[0], time_range[1] - 1)
        
        # Pick a random minute
        random_minute = random.randint(0, 59)
        
        reminder_time = datetime.time(hour=random_hour, minute=random_minute)
        reminder_datetime = datetime.datetime.combine(reminder_date, reminder_time)
        
        reminders.append(reminder_datetime)
    
    # Sort reminders chronologically
    reminders.sort()
    
    # Schedule the reminders
    for reminder_time in reminders:
        if reminder_time > datetime.datetime.now():
            schedule_reminder(reminder_time, message, email_to)
    
    return reminders

def schedule_reminder(reminder_time, message, email_to):
    """Schedule a reminder to be sent at the specified time"""
    def job():
        send_reminder(message, email_to)
    
    # Schedule the job
    schedule.every().day.at(reminder_time.strftime("%H:%M")).do(job).tag(f"reminder_{reminder_time}")
    logger.info(f"Scheduled reminder for {reminder_time.strftime('%Y-%m-%d %H:%M')} to {email_to}")

def send_reminder(message, recipient):
    """Send a reminder email to the specified recipient"""
    # Get email credentials from environment variables
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_server = os.getenv("EMAIL_SERVER", "smtp.mail.yahoo.com")
    email_port = int(os.getenv("EMAIL_PORT", "587"))
    
    logger.debug(f"Email config: Server={email_server}, Port={email_port}, User={email_user}")
    
    # Create email message
    msg = EmailMessage()
    msg.set_content(message)
    msg["Subject"] = "Reminder"
    msg["From"] = email_user
    msg["To"] = recipient
    
    # Send email
    try:
        logger.debug(f"Connecting to {email_server}:{email_port}...")
        
        if email_port == 465:
            # Use SSL connection
            server = smtplib.SMTP_SSL(email_server, email_port)
        else:
            # Use TLS connection
            server = smtplib.SMTP(email_server, email_port)
            server.starttls()
        
        logger.debug("Logging in...")
        server.login(email_user, email_password)
        
        logger.debug(f"Sending email to {recipient}...")
        server.send_message(msg)
        
        logger.debug("Closing connection...")
        server.quit()
        
        logger.info(f"Reminder successfully sent to {recipient} at {datetime.datetime.now()}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reminder: {str(e)}")
        return False

def run_scheduler():
    """Run the scheduler to process scheduled jobs"""
    logger.info("Starting scheduler")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def test_email_connection():
    """Test the email connection without scheduling"""
    email_user = os.getenv("EMAIL_USER")
    recipient = os.getenv("TEST_EMAIL", email_user)
    
    logger.info(f"Testing email connection to {recipient}...")
    result = send_reminder("This is a test reminder from Python Reminder Agent", recipient)
    
    if result:
        logger.info("Email test successful!")
    else:
        logger.error("Email test failed!")
    
    return result

# Example usage
if __name__ == "__main__":
    # Test email connection first
    print("Testing email connection...")
    if test_email_connection():
        print("Email test successful! Now setting up reminders...")
        
        # Set up reminder parameters
        start = datetime.datetime.now()
        end = start + datetime.timedelta(days = 7)  # One week from today
        
        # Create reminder agent
        scheduled_reminders = create_reminder_agent(
            start_date=start,
            end_date=end,
            min_reminders=3,
            max_reminders=5,
            message="Don't forget to drink water!",
            email_to=os.getenv("EMAIL_USER"),  # Send to self for testing
            time_range=(7, 20)  # 9 AM to 8 PM
        )
        
        print(f"Scheduled {len(scheduled_reminders)} reminders:")
        for reminder in scheduled_reminders:
            print(f"  - {reminder.strftime('%Y-%m-%d %H:%M')}")
        
        # Run the scheduler
        run_scheduler()
    else:
        print("Email test failed. Please check your email settings.")