import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import pytesseract
from PIL import Image
import io
import http.server
import socketserver
import threading

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# === ИНЛАЙН КНОПКИ ===
def get_ocr_keyboard():
    keyboard = [
        [InlineKeyboardButton("📷 Распознать текст с фото", callback_data="ocr_help")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton("🔧 Поддержка", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_new_scan_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔄 Распознать другое фото", callback_data="ocr_help")],
        [InlineKeyboardButton("📋 Скопировать текст", callback_data="copy_text")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ОБРАБОТЧИКИ КОМАНД ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = (
        "👋 Привет! Я бот для распознавания текста с изображений.\n\n"
        "📸 Просто отправь мне фотографию с текстом, и я преобразую его в обычный текст.\n\n"
        "✨ Используется Tesseract OCR (бесплатный)\n"
        "🔧 Поддерживает русский и английский языки\n"
        "⚡ Быстрая обработка\n\n"
        "Выбери действие:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_ocr_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "📖 Как пользоваться ботом:\n\n"
        "1. 📷 Отправь мне фотографию с текстом\n"
        "2. ⏳ Подожди несколько секунд\n"
        "3. 📝 Получи распознанный текст\n\n"
        "💡 Советы для лучшего распознавания:\n"
        "• Хорошее освещение\n"
        "• Четкий фокус\n"
        "• Прямой угол съемки\n"
        "• Черный текст на белом фоне\n"
        "• Минимум искажений и теней"
    )
    await update.message.reply_text(help_text, reply_markup=get_ocr_keyboard())

# === ОБРАБОТЧИКИ ИНЛАЙН КНОПОК ===
async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на инлайн кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "ocr_help":
        text = (
            "📸 Чтобы распознать текст:\n\n"
            "1. Сделай фото текста или выбери из галереи\n"
            "2. Отправь фото мне в этот чат\n"
            "3. Я обработаю его и верну текст\n\n"
            "💡 Советы для лучшего распознавания:\n"
            "• Хорошее освещение\n"
            "• Четкий фокус\n"
            "• Прямой угол съемки\n"
            "• Черный текст на белом фоне\n"
            "• Минимум искажений и теней\n\n"
            "Попробуй отправить фото прямо сейчас!"
        )
    elif data == "about":
        text = (
            "ℹ️ О боте:\n\n"
            "• 🤖 Бот для OCR (Optical Character Recognition)\n"
            "• 🖼️ Распознает текст с изображений\n"
            "• 🆓 Использует Tesseract OCR (бесплатно)\n"
            "• ⚡ Быстрая обработка\n"
            "• 🌍 Работает на Render\n"
            "• 🔧 Поддержка русского и английского\n\n"
            "Версия 2.0 - Tesseract Edition\n"
            "Разработано с ❤️ для удобства"
        )
    elif data == "support":
        text = (
            "🔧 Техническая поддержка:\n\n"
            "Если возникли проблемы:\n"
            "• Убедись, что фото четкое\n"
            "• Попробуй другой угол/освещение\n"
            "• Перезапусти бота /start\n\n"
            "Текст не распознается? Попробуй:\n"
            "• Черный текст на белом фоне\n"
            "• Шрифт покрупнее\n"
            "• Меньше теней и бликов\n"
            "• Более контрастное изображение\n\n"
            "По вопросам сотрудничества: @username"
        )
    elif data == "main_menu":
        text = (
            "🏠 Главное меню\n\n"
            "Выбери действие:"
        )
        await query.edit_message_text(text=text, reply_markup=get_ocr_keyboard())
        return
    elif data == "copy_text":
        await query.answer("📋 Скопируйте текст выше", show_alert=True)
        return
    
    await query.edit_message_text(text=text, reply_markup=get_ocr_keyboard())

# === OCR С TESSERACT ===
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изображений с текстом"""
    if not update.message.photo:
        await update.message.reply_text(
            "Пожалуйста, отправьте изображение с текстом.",
            reply_markup=get_ocr_keyboard()
        )
        return

    # Сообщаем пользователю, что началась обработка
    wait_message = await update.message.reply_text("⏳ Обрабатываю изображение...")

    try:
        # Получаем файл изображения (берем самое большое по размеру)
        photo_file = await update.message.photo[-1].get_file()
        # Скачиваем изображение в память (как bytes)
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Конвертируем в PIL Image
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Улучшаем изображение для лучшего распознавания
        # Конвертируем в grayscale (черно-белое)
        image = image.convert('L')
        
        # Распознаем текст с поддержкой русского и английского
        extracted_text = pytesseract.image_to_string(image, lang='rus+eng')
        
        # Проверяем, есть ли распознанный текст
        if extracted_text.strip():
            # Очищаем текст от лишних пробелов
            extracted_text = '\n'.join([line.strip() for line in extracted_text.split('\n') if line.strip()])
            
            # Обрезаем текст если он слишком длинный (ограничение Telegram ~4096 символов)
            if len(extracted_text) > 4000:
                extracted_text = extracted_text[:4000] + "\n\n... (текст обрезан)"
            
            response_text = f"📝 Распознанный текст:\n\n{extracted_text}"
            
            await wait_message.edit_text(response_text, reply_markup=get_new_scan_keyboard())
        else:
            await wait_message.edit_text(
                "❌ Не удалось распознать текст.\n\n"
                "💡 Попробуй:\n"
                "• Более четкое фото\n"
                "• Хорошее освещение\n"
                "• Прямой угол съемки\n"
                "• Черный текст на белом фоне\n"
                "• Увеличить размер текста",
                reply_markup=get_ocr_keyboard()
            )

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await wait_message.edit_text(
            "❌ Произошла ошибка при обработке изображения.\n"
            "Пожалуйста, попробуйте другое изображение.",
            reply_markup=get_ocr_keyboard()
        )

# === ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    
    if text.startswith('/'):
        # Если это команда, игнорируем (обрабатывается другими хендлерами)
        return
    
    await update.message.reply_text(
        "🤖 Я понимаю только изображения с текстом.\n\n"
        "Отправь мне фото, и я распознаю с него текст!\n"
        "Используй кнопки ниже для навигации:",
        reply_markup=get_ocr_keyboard()
    )

# === HTTP SERVER ДЛЯ PING ===
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Отключаем логирование запросов"""
        return

def run_health_server():
    """Запускает HTTP сервер для health checks"""
    port = int(os.environ.get('PORT', 8080))
    with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
        logger.info(f"Health check server running on port {port}")
        httpd.serve_forever()

# === ОСНОВНАЯ ФУНКЦИЯ ===
def main():
    """Запуск бота"""
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex("start"), start))
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex("help"), help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Запускаем HTTP сервер в отдельном потоке
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Запускаем бота
    logger.info("🤖 Бот запущен с Tesseract OCR...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
