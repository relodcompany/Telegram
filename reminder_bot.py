import datetime
import os
import re
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN", "8514134989:AAEFpZHK_MGNHx5P8H1INDb186iglSbZeas")
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

    is_yearly = "every year" in time_str or "yearly" in time_str

    match_relative = re.search(r"in\s+(\d+)\s+(second|minute|hour|day)s?", time_str)
    if match_relative:
        val = int(match_relative.group(1))
        unit = match_relative.group(2)
        if unit == "second":
            return now + datetime.timedelta(seconds=val), False
        if unit == "minute":
            return now + datetime.timedelta(minutes=val), False
        if unit == "hour":
            return now + datetime.timedelta(hours=val), False
        if unit == "day":
            return now + datetime.timedelta(days=val), False

    match_time = re.search(r"(?:at\s+)?(\d{1,2})(?::(\d{2}))?(?:\s*(am|pm))?", time_str)
    hour, minute = 9, 0
    if match_time:
        h = int(match_time.group(1))
        m = int(match_time.group(2)) if match_time.group(2) else 0
        ampm = match_time.group(3)
        if ampm == "pm" and h < 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        hour, minute = h, m

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    match_date1 = re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s*,?\s*(\d{4}))?",
        time_str,
    )
    match_date2 = re.search(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?",
        time_str,
    )

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
            target_time = now.replace(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )
        except ValueError:
            return None, False

        if not year_str and target_time <= now:
            try:
                target_time = target_time.replace(year=year + 1)
            except ValueError:
                target_time += datetime.timedelta(days=365)

        return target_time, is_yearly

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    found_weekday = None
    for day_name, day_int in weekdays.items():
        if day_name in time_str:
            found_weekday = day_int
            break

    try:
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return None, False

    if found_weekday is not None:
        days_ahead = found_weekday - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and target_time <= now):
            days_ahead += 7
        target_time += datetime.timedelta(days=days_ahead)
        return target_time, is_yearly

    if "tomorrow" in time_str:
        target_time += datetime.timedelta(days=1)
        return target_time, is_yearly

    if match_time:
        if target_time <= now:
            target_time += datetime.timedelta(days=1)
        return target_time, is_yearly

    return None, False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    del context
    if update.message is None:
        return

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
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse the user's input and schedule a reminder."""
    try:
        if update.message is None or not update.message.text:
            return

        user_input = update.message.text.replace("/remind", "", 1).strip()

        if ";" not in user_input:
            await update.message.reply_text(
                "❌ Invalid format. Use: `/remind <time> ; <message>`", parse_mode="Markdown"
            )
            return

        time_str, message_str = user_input.split(";", 1)
        parsed_time, is_yearly = parse_time_input(time_str)

        if not parsed_time:
            await update.message.reply_text(f"❌ Sorry, I couldn't understand the time: '{time_str}'.")
            return

        now = datetime.datetime.now(BOT_TIMEZONE)
        if parsed_time <= now:
            await update.message.reply_text("⏳ That time is in the past! Please provide a future time.")
            return

        if context.job_queue is None:
            await update.message.reply_text(
                "🚨 **SYSTEM ERROR:** JobQueue is unavailable. Install `python-telegram-bot[job-queue]`.",
                parse_mode="Markdown",
            )
            return

        job_data = {
            "message": message_str.strip(),
            "is_yearly": is_yearly,
            "target_time": parsed_time,
        }

        context.job_queue.run_once(
            send_reminder,
            when=parsed_time,
            chat_id=update.effective_chat.id,
            data=job_data,
        )

        formatted_time = parsed_time.strftime("%B %d, %Y at %H:%M %Z")
        recurrence_text = "\n🔁 **(Repeats Every Year)**" if is_yearly else ""
        await update.message.reply_text(
            f"✅ Got it! I will remind you to:\n\n**{message_str.strip()}**\n\n🕒 At: {formatted_time}{recurrence_text}",
            parse_mode="Markdown",
        )

    except Exception:
        import traceback

        error_msg = traceback.format_exc()
        if update.message is not None:
            await update.message.reply_text(
                f"⚠️ **CRASH DETECTED:**\n\n```python\n{error_msg[-800:]}\n```",
                parse_mode="Markdown",
            )
        print(error_msg)


async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by JobQueue when the timer goes off."""
    job = context.job
    job_data = job.data

    await context.bot.send_message(
        chat_id=job.chat_id,
        text=f"⏰ **REMINDER:**\n\n{job_data['message']}",
        parse_mode="Markdown",
    )

    if job_data["is_yearly"] and context.job_queue is not None:
        old_time = job_data["target_time"]
        try:
            next_time = old_time.replace(year=old_time.year + 1)
        except ValueError:
            next_time = old_time + datetime.timedelta(days=365)

        now = datetime.datetime.now(BOT_TIMEZONE)
        if next_time <= now:
            next_time = now + datetime.timedelta(days=365)

        job_data["target_time"] = next_time
        context.job_queue.run_once(
            send_reminder,
            when=next_time,
            chat_id=job.chat_id,
            data=job_data,
        )


def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    app = Application.builder().token(BOT_TOKEN).timezone(BOT_TIMEZONE).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", set_reminder))

    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
