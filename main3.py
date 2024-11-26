#!/usr/bin/env python
# pylint: disable=unused-argument
import logging
import os
from datetime import datetime, time
from collections import defaultdict
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TELEGRAM_TOKEN:
    raise ValueError("Por favor, configure la variable TELEGRAM_TOKEN en el archivo .env")

USERS_TO_NOTIFY = [
    123456789,
    987654321
]

# Callbacks para los botones
CALLBACK_ADD = "add_info"
CALLBACK_SUMMARY = "view_summary"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

messages_history = defaultdict(lambda: defaultdict(list))

def get_keyboard():
    """Create the inline keyboard markup"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Añadir información", callback_data=CALLBACK_ADD),
            InlineKeyboardButton("📊 Ver resumen", callback_data=CALLBACK_SUMMARY)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def log_message(user, message):
    """Log message to history.txt file and store in messages history"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H:%M")
    
    with open("history.txt", "a", encoding="utf-8") as f:
        f.write(f"[{current_date} {timestamp}] Usuario: {user.full_name} (ID: {user.id}) - Mensaje: {message}\n")
    
    messages_history[current_date][user.full_name].append({
        'time': timestamp,
        'message': message
    })

def generate_daily_summary(date=None):
    """Generate a formatted summary of messages for a specific date"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    if date not in messages_history or not messages_history[date]:
        return f"No hay mensajes para mostrar del día {date}"
    
    summary = f"📝 Resumen de mensajes del {date}:\n\n"
    
    for user, messages in sorted(messages_history[date].items()):
        summary += f"👤 {user}:\n"
        for msg in sorted(messages, key=lambda x: x['time']):
            summary += f"   [{msg['time']}] {msg['message']}\n"
        summary += "\n"
    
    return summary

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Usa los botones para interactuar conmigo:",
        reply_markup=get_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Puedes usar los botones o estos comandos:\n"
        "/start - Iniciar bot y mostrar botones\n"
        "/help - Mostrar ayuda\n"
        "/resumen YYYY-MM-DD - Ver resumen de un día específico",
        reply_markup=get_keyboard()
    )

async def get_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /resumen command"""
    try:
        if context.args:
            date = context.args[0]
            datetime.strptime(date, "%Y-%m-%d")
        else:
            date = datetime.now().strftime("%Y-%m-%d")
            
        summary = generate_daily_summary(date)
        await update.message.reply_text(summary, reply_markup=get_keyboard())
    except ValueError:
        await update.message.reply_text("Formato de fecha incorrecto. Usa YYYY-MM-DD")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages"""
    user = update.effective_user
    message = update.message.text
    log_message(user, message)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses"""
    query = update.callback_query
    await query.answer()  # Responde al callback query

    if query.data == CALLBACK_ADD:
        await query.message.reply_text("¿Qué has hecho hoy?", reply_markup=get_keyboard())
    elif query.data == CALLBACK_SUMMARY:
        summary = generate_daily_summary()
        await query.message.reply_text(summary, reply_markup=get_keyboard())

async def send_daily_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily summary to specified users"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    summary = generate_daily_summary(current_date)
    
    for user_id in USERS_TO_NOTIFY:
        try:
            await context.bot.send_message(
                chat_id=user_id, 
                text=summary,
                parse_mode='HTML',
                reply_markup=get_keyboard()
            )
            logger.info(f"Resumen diario enviado al usuario {user_id}")
        except Exception as e:
            logger.error(f"Error enviando resumen al usuario {user_id}: {e}")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    job_queue = application.job_queue
    job_queue.run_daily(send_daily_summary, time=time(hour=21, minute=0))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("resumen", get_summary))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()