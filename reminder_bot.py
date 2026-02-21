import re
import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Replace with your actual Bot Token
BOT_TOKEN = "8514134989:AAEFpZHK_MGNHx5P8H1INDb186iglSbZeas"
BOT_TIMEZONE = ZoneInfo("Europe/Moscow")

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
    now = datetime.datetime.now(BOT_TIMEZONE)
    
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

@@ -124,118 +126,118 @@ async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        "• `March 15 every year` (recurring!)\n\n"
        "**Example:**\n"
        "👉 `/remind 15th March every year ; Pay yearly server hosting bill`\n"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse the user's input and schedule a reminder with error catching."""
    try:
        user_input = update.message.text.replace('/remind', '', 1).strip()
        
        if ';' not in user_input:
            await update.message.reply_text("❌ Invalid format. Use: `/remind <time> ; <message>`", parse_mode='Markdown')
            return
        
        time_str, message_str = user_input.split(';', 1)
        
        # Use our custom built-in parser
        result = parse_time_input(time_str)
        parsed_time, is_yearly = result
        
        if not parsed_time:
            await update.message.reply_text(f"❌ Sorry, I couldn't understand the time: '{time_str}'.")
            return
        
        now = datetime.datetime.now(BOT_TIMEZONE)

        if parsed_time <= now:
            await update.message.reply_text("⏳ That time is in the past! Please provide a future time.")
            return

        job_data = {
            'message': message_str.strip(),
            'is_yearly': is_yearly,
            'target_time': parsed_time
        }

        # Check if the job_queue is actually loaded
        if context.job_queue is None:
            await update.message.reply_text("🚨 **SYSTEM ERROR:** The JobQueue failed to load. APScheduler might not be installed correctly on Bothost.", parse_mode='Markdown')
            return

        # Schedule the task
        context.job_queue.run_once(␊
            send_reminder,␊
            when=parsed_time,
            chat_id=update.effective_chat.id,␊
            data=job_data␊
        )␊
␊
        formatted_time = parsed_time.strftime('%B %d, %Y at %H:%M %Z')
        recurrence_text = "🔁 **(Repeats Every Year)**" if is_yearly else ""
        
        await update.message.reply_text(
            f"✅ Got it! I will remind you to:\n\n**{message_str.strip()}**\n\n🕒 At: {formatted_time}\n{recurrence_text}", 
            parse_mode='Markdown'
        )

    except Exception as e:
        # IF ANYTHING BREAKS, SEND THE ERROR TO TELEGRAM!
        import traceback
        error_msg = traceback.format_exc()
        await update.message.reply_text(f"⚠️ **CRASH DETECTED:**\n\n```python\n{error_msg[-800:]}\n```", parse_mode='Markdown')
        print(error_msg)

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
            
        now = datetime.datetime.now(BOT_TIMEZONE)
        if next_time <= now:
            next_time = now + datetime.timedelta(days=365)
        
        # Update the target time in the memory block
        job_data['target_time'] = next_time
        
        # Put it back in the queue for next year
        context.job_queue.run_once(␊
            send_reminder,␊
            when=next_time,
            chat_id=job.chat_id,␊
            data=job_data␊
        )␊

def main() -> None:
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).timezone(BOT_TIMEZONE).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", set_reminder))

    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

