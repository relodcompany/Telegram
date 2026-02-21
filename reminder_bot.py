import datetime
import dateparser
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Replace with your actual Bot Token
BOT_TOKEN = "8514134989:AAG5olQEVoAeqR1tZY-HRN4T_HLnQqiGjko"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_text = (
        "👋 Hi! I am your Reminder Bot.\n\n"
        "To set a reminder, use the /remind command followed by the time and your message, separated by a semicolon (;).\n\n"
        "**Examples:**\n"
        "👉 `/remind in 10 minutes ; Take out the trash`\n"
        "👉 `/remind tomorrow at 9 AM ; Call the doctor`\n"
        "👉 `/remind Friday at 5 PM ; Weekend starts now!`"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse the user's input and schedule a reminder."""
    # Extract the text after the /remind command
    user_input = update.message.text.replace('/remind', '', 1).strip()
    
    # Check if the format is correct (must contain a semicolon)
    if ';' not in user_input:
        await update.message.reply_text(
            "❌ Invalid format.\n"
            "Please use: `/remind <time> ; <message>`\n"
            "Example: `/remind in 5 minutes ; Check the oven`",
            parse_mode='Markdown'
        )
        return
    
    # Split the input into time and message
    time_str, message_str = user_input.split(';', 1)
    time_str = time_str.strip()
    message_str = message_str.strip()

    # Parse the natural language time string into a datetime object
    parsed_time = dateparser.parse(time_str)
    
    if not parsed_time:
        await update.message.reply_text(f"❌ Sorry, I couldn't understand the time: '{time_str}'")
        return
    
    # Calculate how many seconds from now the reminder should trigger
    now = datetime.datetime.now()
    delay_seconds = (parsed_time - now).total_seconds()

    if delay_seconds <= 0:
        await update.message.reply_text("⏳ That time is in the past! Please provide a future time.")
        return

    # Schedule the task in the JobQueue
    context.job_queue.run_once(
        send_reminder,
        when=delay_seconds,
        chat_id=update.effective_chat.id,
        data=message_str  # Pass the message to the scheduled job
    )

    # Confirm with the user
    formatted_time = parsed_time.strftime('%Y-%m-%d %H:%M:%S')
    await update.message.reply_text(f"✅ Got it! I will remind you to:\n\n**{message_str}**\n\n🕒 At: {formatted_time}", parse_mode='Markdown')

async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """This function is called by the JobQueue when the timer goes off."""
    job = context.job
    # Send the reminder message back to the chat ID
    await context.bot.send_message(
        chat_id=job.chat_id, 
        text=f"⏰ **REMINDER:**\n\n{job.data}",
        parse_mode='Markdown'
    )

def main() -> None:
    """Start the bot."""
    # Build the application with your bot token
    app = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", set_reminder))

    # Run the bot until the user presses Ctrl-C
    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()