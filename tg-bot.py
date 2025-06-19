import os
import logging
import io
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext, CallbackQueryHandler
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "токен скрыт")
OCR_SERVICE_URL = "http://localhost:8000/recognize"


pdfmetrics.registerFont(TTFont("Arial", "C:\\Windows\\Fonts\\arial.ttf"))

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привет!\n"
        "Отправьте фото с текстом.\n"
        "Будет выполнено распознавание текста."
    )

def handle_photo(update: Update, context: CallbackContext):
    try:
        photo_file = update.message.photo[-1].get_file()
        photo_bytes = io.BytesIO()
        photo_file.download(out=photo_bytes)
        photo_bytes.seek(0)
        update.message.reply_text("🔄 Распознаю текст на фото...")
        files = {'file': ('image.png', photo_bytes.getvalue())}
        data = {'lang_mode': 'auto'}
        response = requests.post(OCR_SERVICE_URL, files=files, data=data)
        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '')
            status = result.get('status', '')
            if status == 'empty':
                update.message.reply_text("Пожалуйста, отправьте фото с текстом.")
            elif text.strip():
                context.user_data['recognized_text'] = text
                keyboard = [[InlineKeyboardButton("Конвертировать в PDF", callback_data="to_pdf")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(f"📝 Распознанный текст:\n{text}", reply_markup=reply_markup)
            else:
                update.message.reply_text("Текст не найден или не распознан.")
        else:
            update.message.reply_text("Ошибка при обращении к сервису распознавания.")
        context.user_data['photo_bytes'] = photo_bytes.getvalue()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        update.message.reply_text(f"Ошибка обработки: {str(e)}")

def handle_non_photo(update: Update, context: CallbackContext):
    update.message.reply_text("Пожалуйста, отправьте фото с текстом.")

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if query.data == "to_pdf":
        text = context.user_data.get('recognized_text', '')
        if not text.strip():
            query.message.reply_text("Нет текста для конвертации.")
            return
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer)
        c.setFont("Arial", 12)
        text_object = c.beginText(40, 800)
        for line in text.split('\n'):
            text_object.textLine(line)
        c.drawText(text_object)
        c.save()
        pdf_buffer.seek(0)
        query.message.reply_document(document=InputFile(pdf_buffer, filename="recognized_text.pdf"))

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(MessageHandler(~Filters.photo, handle_non_photo))
    dp.add_handler(CallbackQueryHandler(button_callback))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()