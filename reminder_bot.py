import re
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Replace with your actual Bot Token
BOT_TOKEN = "8514134989:AAG5olQEVoAeqR1tZY-HRN4T_HLnQqiGjko"

def parse_time_input(time_str: str):
    """
    Advanced time parser. Supports:
    - Relative: "in 10 minutes"
    - Weekdays: "Friday at 5pm"
    - Dates: "15th March 2026", "March 15"
    - Recurring: "15th March every year"
    
    Returns a tuple: (target_datetime, is_yearly_boolean)
    """
    time_str = time_str.lower().strip()
    now = datetime.datetime.now()
    
    # Check if this is a recurring yearly reminder
    is_yearly = 'every year' in time_str or 'yearly' in time_str

    # 1. Parse relative time: "in 10 minutes"
    match_relative = re.search(r'in\s+(\d+)\s+(second|minute|hour|day)s?', time_str)
    if match_relative:
        val = int(match_relative.group(1))
        unit = match_relative.group(2)
        if unit == 'second': return now + datetime.timedelta(seconds=val), False
        if unit == 'minute': return now + datetime.timedelta(minutes=val), False
        if unit == 'hour': return now + datetime.timedelta(hours=val), False
        if unit == 'day': return now + datetime.timedelta(days=val), False

    # Extract specific time if mentioned (e.g., "at 15:30" or "at 5 pm")
    match_time = re.search(r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?(?:\s*(am|pm))?', time_str)
    hour, minute = 9, 0 # Default time is 9:00 AM if no time is given
    if match_time:
        h = int(match_time.group(1))
        m = int(match_time.group(2)) if match_time.group(2) else 0
        ampm = match_time.group(3)
        if ampm == 'pm' and h < 12: h += 12
        elif ampm == 'am' and h == 12: h = 0
        hour, minute = h, m

    # 2. Parse Specific Dates (e.g. "15th march 2026", "march 15")
    month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 
                 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
    
    # Matches "15th March 2026"
    match_date1 = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s*,?\s*(\d{4}))?', time_str)
    # Matches "March 15th 2026"
    match_date2 = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?', time_str)
    
    day_str = month_str = year_str = None
    if match_date1:
        day_str, month_str, year_str = match_date1.groups()
    elif match_date2:
        month_str, day_str, year_str = match_date2.groups()

    if day_str and month_str:
        day = int(day_str)
        month = month_map[month_str[:3]]
        year = int(year_str) if year_str else now.year
        
        try:
            target_time = now.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            return None, False # Failsafe for things like Feb 30th
            
        # If no year was typed, and the date has already passed this year, jump to next year
        if not year_str and target_time <= now:
            try:
                target_time = target_time.replace(year=year + 1)
            except ValueError: 
                target_time += datetime.timedelta(days=365) # Leap year failsafe
                
        return target_time, is_yearly

    # 3. Parse specific day of the week (e.g., "Friday")
    weekdays = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
    found_weekday = None
    for day_name, day_int in weekdays.items():
        if day_name in time_str:
            found_weekday = day_int
            break

    try:
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return None, False 

    # If a weekday was found
    if found_weekday is not None:
        days_ahead = found_weekday - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and target_time <= now):
            days_ahead += 7
        target_time += datetime.timedelta(days=days_ahead)
        return target_time, is_yearly

    # 4. If "tomorrow" was found
    if 'tomorrow' in time_str:
        target_time += datetime.timedelta(days=1)
        return target_time, is_yearly

    # 5. If only a time was mentioned (e.g., "at 15:00")
    if match_time:
        if target_time <= now:
            target_time += datetime.timedelta(days=1)
        return target_time, is_yearly

    return None, False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_text = (
        "👋 Hi! I am your Reminder Bot.\n\n"
        "To set a reminder, use the /remind command followed by the time and your message, separated by a semicolon (;).\n\n"
        "**Supported Formats:**\n"
        "• `in X minutes/hours/days`\n"
        "• `tomorrow at HH:MM`\n"
        "• `Friday at 5 pm`\n"
        "• `15th March 2026 at 14:00`\n"
        "• `March 15 every year` (recurring!)\n\n"
        "**Example:**\n"
        "👉 `/remind 15th March every year ; Pay yearly server hosting bill`\n"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse the user's input and schedule a reminder."""
    user_input = update.message.text.replace('/remind', '', 1).strip()
    
    if ';' not in user_input:
        await update.message.reply_text("❌ Invalid format. Use: `/remind <time> ; <message>`", parse_mode='Markdown')
        return
    
    time_str, message_str = user_input.split(';', 1)
    
    # Use our custom built-in parser, which now returns two items
    result = parse_time_input(time_str)
    parsed_time, is_yearly = result
    
    if not parsed_time:
        await update.message.reply_text(f"❌ Sorry, I couldn't understand the time: '{time_str}'.")
        return
    
    now = datetime.datetime.now()
    delay_seconds = (parsed_time - now).total_seconds()

    if delay_seconds <= 0:
        await update.message.reply_text("⏳ That time is in the past! Please provide a future time.")
        return

    # Package the data so the bot remembers if it needs to repeat next year
    job_data = {
        'message': message_str.strip(),
        'is_yearly': is_yearly,
        'target_time': parsed_time
    }

    # Schedule the task
    context.job_queue.run_once(
        send_reminder,
        when=delay_seconds,
        chat_id=update.effective_chat.id,
        data=job_data
    )

    formatted_time = parsed_time.strftime('%B %d, %Y at %H:%M')
    recurrence_text = "🔁 **(Repeats Every Year)**" if is_yearly else ""
    
    await update.message.reply_text(
        f"✅ Got it! I will remind you to:\n\n**{message_str.strip()}**\n\n🕒 At: {formatted_time}\n{recurrence_text}", 
        parse_mode='Markdown'
    )

async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by JobQueue when the timer goes off."""
    job = context.job
    job_data = job.data

    # 1. Send the message to the user
    await context.bot.send_message(
        chat_id=job.chat_id, 
        text=f"⏰ **REMINDER:**\n\n{job_data['message']}",
        parse_mode='Markdown'
    )

    # 2. If it is a yearly reminder, reschedule it for next year!
    if job_data['is_yearly']:
        old_time = job_data['target_time']
        try:
            # Add exactly 1 year
            next_time = old_time.replace(year=old_time.year + 1)
        except ValueError:
            # Failsafe for Leap Years (Feb 29)
            next_time = old_time + datetime.timedelta(days=365)
            
        now = datetime.datetime.now()
        delay_seconds = (next_time - now).total_seconds()
        
        # Update the target time in the memory block
        job_data['target_time'] = next_time
        
        # Put it back in the queue for next year
        context.job_queue.run_once(
            send_reminder,
            when=delay_seconds,
            chat_id=job.chat_id,
            data=job_data
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


