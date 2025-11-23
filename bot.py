import logging
import os
import subprocess
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

# === ПРОВЕРКА УСТАНОВКИ TESSERACT ===
def check_tesseract():
    """Проверяет установлен ли Tesseract и устанавливает если нет"""
    try:
        # Пытаемся найти путь к tesseract
        tesseract_path = subprocess.check_output(['which', 'tesseract']).decode().strip()
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        logger.info(f"Tesseract найден: {tesseract_path}")
        return True
    except:
        logger.warning("Tesseract не найден, пытаемся установить...")
        try:
            # Устанавливаем tesseract через apt
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'tesseract-ocr', 'tesseract-ocr-rus', 'tesseract-ocr-eng'], check=True)
            
            # Обновляем путь
            tesseract_path = subprocess.check_output(['which', 'tesseract']).decode().strip()
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info("Tesseract успешно установлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка установки Tesseract: {e}")
            return False

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
        [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ОБРАБОТЧИКИ КОМАНД ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    help_text = (
        "📖 Как пользоваться ботом:\n\n"
        "1. 📷 Отправь мне фотографию с текстом\n"
        "2. ⏳ Подожди несколько секунд\n"
        "3. 📝 Получи распознанный текст\n\n"
        "💡 Советы для лучшего распознавания:\n"
        "• Хорошее освещение\n"
        "• Четкий фокус\n"
        "• Прямой угол съемки\n"
        "• Черный текст на белом фоне"
    )
    await update.message.reply_text(help_text, reply_markup=get_ocr_keyboard())

# === ОБРАБОТЧИКИ ИНЛАЙН КНОПОК ===
async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "ocr_help":
        text = (
            "📸 Чтобы распознать текст:\n\n"
            "1. Сделай фото текста или выбери из галереи\n"
            "2. Отправь фото мне в этот чат\n"
            "3. Я обработаю его и верну текст\n\n"
            "Попробуй отправить фото прямо сейчас!"
        )
    elif data == "about":
        text = (
            "ℹ️ О боте:\n\n"
            "• 🤖 Бот для OCR (Optical Character Recognition)\n"
            "• 🖼️ Распознает текст с изображений\n"
            "• 🆓 Использует Tesseract OCR (бесплатно)\n"
            "• ⚡ Быстрая обработка\n"
            "• 🌍 Работает на Render\n\n"
            "Версия 2.0 - Tesseract Edition"
        )
    elif data == "support":
        text = (
            "🔧 Техническая поддержка:\n\n"
            "Если возникли проблемы:\n"
            "• Убедись, что фото четкое\n"
            "• Попробуй другой угол/освещение\n"
            "• Перезапусти бота /start\n\n"
            "По вопросам сотрудничества: @username"
        )
    elif data == "main_menu":
        text = "🏠 Главное меню\n\nВыбери действие:"
        await query.edit_message_text(text=text, reply_markup=get_ocr_keyboard())
        return
    
    await query.edit_message_text(text=text, reply_markup=get_ocr_keyboard())

# === OCR С TESSERACT ===
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(
            "Пожалуйста, отправьте изображение с текстом.",
            reply_markup=get_ocr_keyboard()
        )
        return

    wait_message = await update.message.reply_text("⏳ Обрабатываю изображение...")

    try:
        # Скачиваем изображение
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Конвертируем в PIL Image
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Улучшаем изображение для лучшего распознавания
        image = image.convert('L')  # В grayscale
        
        # Распознаем текст
        extracted_text = pytesseract.image_to_string(image, lang='rus+eng')
        
        if extracted_text.strip():
            # Очищаем текст
            extracted_text = '\n'.join([line.strip() for line in extracted_text.split('\n') if line.strip()])
            
            # Обрезаем если слишком длинный
            if len(extracted_text) > 4000:
                extracted_text = extracted_text[:4000] + "\n\n... (текст обрезан)"
            
            response_text = f"📝 Распознанный текст:\n\n{extracted_text}"
            
            await wait_message.edit_text(response_text, reply_markup=get_new_scan_keyboard())
        else:
            await wait_message.edit_text(
                "❌ Не удалось распознать текст.\n\n"
                "Попробуй:\n"
                "• Более четкое фото\n"
                "• Хорошее освещение\n"
                "• Прямой угол съемки",
                reply_markup=get_ocr_keyboard()
            )

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await wait_message.edit_text(
            "❌ Ошибка при обработке изображения.",
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
        return

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
        logger.info(f"Health check server running on port {port}")
        httpd.serve_forever()

# === ОСНОВНАЯ ФУНКЦИЯ ===
def main():
    # Проверяем и устанавливаем Tesseract при необходимости
    if not check_tesseract():
        logger.error("Не удалось установить Tesseract. Бот не может работать.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex("start"), start))
    application.add_handler(MessageHandler(filters.COMMAND & filters.Regex("help"), help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Запускаем HTTP сервер для health checks
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    print("🤖 Бот запущен с Tesseract OCR...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
