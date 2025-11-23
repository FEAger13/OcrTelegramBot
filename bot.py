import os
import logging
import requests
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import http.server
import socketserver
import threading

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📷 Распознать текст", callback_data="ocr_help")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "👋 Привет! Отправь мне фото с текстом, и я распознаю его!"
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "ocr_help":
        text = "📸 Отправь мне фото с текстом!"
        await query.edit_message_text(text=text, reply_markup=get_back_keyboard())
    elif query.data == "about":
        text = "🤖 Бот для распознавания текста с фото"
        await query.edit_message_text(text=text, reply_markup=get_back_keyboard())
    elif query.data == "back":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_keyboard())

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wait_msg = await update.message.reply_text("⏳ Распознаю текст...")
    
    try:
        # Скачиваем фото
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Используем бесплатный OCR API
        api_key = "K89936196688957"  # бесплатный ключ
        base64_image = base64.b64encode(photo_bytes).decode()
        
        response = requests.post(
            'https://api.ocr.space/parse/image',
            data={
                'apikey': api_key,
                'base64Image': f'data:image/jpeg;base64,{base64_image}',
                'language': 'rus',
                'isOverlayRequired': False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['IsErroredOnProcessing']:
                text = "❌ Не удалось распознать текст"
            else:
                extracted_text = result['ParsedResults'][0]['ParsedText']
                text = f"📝 Распознанный текст:\n\n{extracted_text}"
        else:
            text = "❌ Ошибка API"
            
    except Exception as e:
        logger.error(f"OCR error: {e}")
        text = "❌ Ошибка при обработке фото"
    
    await wait_msg.edit_text(text, reply_markup=get_main_keyboard())

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
        logger.info(f"Health server on port {port}")
        httpd.serve_forever()

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex("start"), start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(CallbackQueryHandler(handle_button_click))
    
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
