import re
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Replace with your actual Bot Token
BOT_TOKEN = "8514134989:AAG5olQEVoAeqR1tZY-HRN4T_HLnQqiGjko"

def parse_time_input(time_str: str):
    """
    A custom, lightweight time parser using Python's built-in 're' and 'datetime' libraries.
    No external dependencies (like dateparser) are required.
    """
    time_str = time_str.lower().strip()
    now = datetime.datetime.now()
    
    # 1. Parse relative time: "in 10 minutes", "in 2 hours", "in 1 day"
    match_relative = re.search(r'in\s+(\d+)\s+(second|minute|hour|day)s?', time_str)
    if match_relative:
        val = int(match_relative.group(1))
        unit = match_relative.group(2)
        if unit == 'second': return now + datetime.timedelta(seconds=val)
        if unit == 'minute': return now + datetime.timedelta(minutes=val)
        if unit == 'hour': return now + datetime.timedelta(hours=val)
        if unit == 'day': return now + datetime.timedelta(days=val)

    # 2. Parse absolute time: "at 15:30", "tomorrow at 9 am", "at 5 pm"
    match_absolute = re.search(r'(?:tomorrow\s+)?at\s+(\d{1,2})(?::(\d{2}))?(?:\s*(am|pm))?', time_str)
    if match_absolute:
        hour = int(match_absolute.group(1))
        minute = int(match_absolute.group(2)) if match_absolute.group(2) else 0
        ampm = match_absolute.group(3)
        
        # Convert 12-hour format to 24-hour format
        if ampm == 'pm' and hour < 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
            
        try:
            # Set the time for today
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            return None # Failsafe for invalid times (like 25:61)
            
        # Move forward a day if "tomorrow" is specified, OR if the time has already passed today
        if 'tomorrow' in time_str:
            target_time += datetime.timedelta(days=1)
        elif target_time <= now:
            target_time += datetime.timedelta(days=1)
            
        return target_time

    return None # Return None if the bot couldn't understand the format

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_text = (
        "👋 Hi! I am your Reminder Bot.\n\n"
        "To set a reminder, use the /remind command followed by the time and your message, separated by a semicolon (;).\n\n"
        "**Supported Formats:**\n"
        "• `in X minutes/hours/days`\n"
        "• `at HH:MM` (e.g., at 15:30 or at 5 pm)\n"
        "• `tomorrow at HH:MM`\n\n"
        "**Examples:**\n"
        "👉 `/remind in 10 minutes ; Take out the trash`\n"
        "👉 `/remind tomorrow at 9 am ; Call the doctor`\n"
        "👉 `/remind at 18:30 ; Feed the cat`"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse the user's input and schedule a reminder."""
    user_input = update.message.text.replace('/remind', '', 1).strip()
    
    if ';' not in user_input:
        await update.message.reply_text(
            "❌ Invalid format.\n"
            "Please use: `/remind <time> ; <message>`\n"
            "Example: `/remind in 5 minutes ; Check the oven`",
            parse_mode='Markdown'
        )
        return
    
    time_str, message_str = user_input.split(';', 1)
    
    # Use our custom built-in parser
    parsed_time = parse_time_input(time_str)
    
    if not parsed_time:
        await update.message.reply_text(
            f"❌ Sorry, I couldn't understand the time: '{time_str}'.\n"
            "Please use formats like 'in 10 minutes', 'at 15:30', or 'tomorrow at 9 am'."
        )
        return
    
    now = datetime.datetime.now()
    delay_seconds = (parsed_time - now).total_seconds()

    if delay_seconds <= 0:
        await update.message.reply_text("⏳ That time is in the past! Please provide a future time.")
        return

    # Schedule the task
    context.job_queue.run_once(
        send_reminder,
        when=delay_seconds,
        chat_id=update.effective_chat.id,
        data=message_str.strip() 
    )

    formatted_time = parsed_time.strftime('%Y-%m-%d %H:%M:%S')
    await update.message.reply_text(
        f"✅ Got it! I will remind you to:\n\n**{message_str.strip()}**\n\n🕒 At: {formatted_time}", 
        parse_mode='Markdown'
    )

async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by JobQueue when the timer goes off."""
    job = context.job
    await context.bot.send_message(
        chat_id=job.chat_id, 
        text=f"⏰ **REMINDER:**\n\n{job.data}",
        parse_mode='Markdown'
    )

def main() -> None:
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", set_reminder))

    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
