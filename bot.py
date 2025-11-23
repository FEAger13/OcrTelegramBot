import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import http.server
import socketserver
import threading

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')

def get_ocr_keyboard():
    keyboard = [
        [InlineKeyboardButton("📷 Распознать текст", callback_data="ocr_help")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "👋 Привет! Я бот для распознавания текста. Отправь мне фото с текстом!"
    await update.message.reply_text(welcome_text, reply_markup=get_ocr_keyboard())

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "ocr_help":
        text = "📸 Отправь мне фото с текстом, и я распознаю его!"
    elif query.data == "about":
        text = "ℹ️ Бот для OCR. Версия 1.0"
    
    await query.edit_message_text(text=text, reply_markup=get_ocr_keyboard())

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🔄 Функция распознавания текста скоро будет доступна!"
    await update.message.reply_text(text, reply_markup=get_ocr_keyboard())

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
        logger.info(f"Health check server running on port {port}")
        httpd.serve_forever()

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex("start"), start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(CallbackQueryHandler(handle_button_click))

    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    logger.info("🤖 Бот запущен...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
