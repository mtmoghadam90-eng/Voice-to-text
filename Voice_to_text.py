import os
import json
import requests
import asyncio
import threading
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask

# --- تنظیمات اصلی از Environment Variables ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SPEECHMATICS_API_KEY = os.environ.get("SPEECHMATICS_API_KEY")
SPEECHMATICS_URL = "https://asr.api.speechmatics.com/v2/jobs/"

# --- بخش ربات تلگرام (بدون تغییر) ---
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # این تابع دقیقاً مانند قبل است
    file_id = update.message.audio.file_id
    new_file = await context.bot.get_file(file_id)
    file_path = f"{file_id}.oga"
    await new_file.download_to_drive(file_path)
    await update.message.reply_text("فایل صوتی دریافت شد. در حال پردازش... 🤖")
    try:
        speechmatics_config = {"type": "transcription", "transcription_config": {"language": "fa"}}
        with open(file_path, 'rb') as f:
            files = {'data_file': f, 'config': (None, json.dumps(speechmatics_config))}
            headers = {'Authorization': f'Bearer {SPEECHMATICS_API_KEY}'}
            response = requests.post(SPEECHMATICS_URL, headers=headers, files=files)
            response.raise_for_status()
            job_id = response.json()['id']
        result_url = f"{SPEECHMATICS_URL}{job_id}/transcript?format=txt"
        while True:
            result_response = requests.get(result_url, headers=headers)
            if result_response.status_code == 200:
                transcribed_text = result_response.text
                break
            elif result_response.status_code == 404:
                await asyncio.sleep(10)
            else:
                result_response.raise_for_status()
        text_file_path = f"{job_id}.txt"
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(transcribed_text)
        await update.message.reply_document(document=open(text_file_path, "rb"), filename="Transcription.txt")
        os.remove(file_path)
        os.remove(text_file_path)
    except Exception as e:
        print(f"An error occurred: {e}")
        await update.message.reply_text(f"متاسفانه در پردازش فایل خطایی رخ داد.")

async def main_bot():
    """تابع اصلی برای اجرای ربات."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    print("Bot is starting in async mode...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

# --- بخش وب سرور Flask ---
app = Flask(__name__)

@app.route('/')
def index():
    """یک صفحه وب ساده برای پاسخ به Render."""
    return "Bot is running!"

def run_flask():
    """وب سرور را اجرا می‌کند."""
    # پورت توسط Render به صورت خودکار تنظیم می‌شود
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- اجرای همزمان هر دو ---
if __name__ == "__main__":
    # اجرای ربات در یک ترد جداگانه
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_until_complete(main_bot())
    
    # اجرای وب سرور در ترد اصلی
    # (این بخش به دلیل ساختار Render اجرا نخواهد شد، اما برای تست محلی مفید است)
    # Render فقط `run_flask` را از طریق Start Command اجرا می‌کند
    # برای حل این مشکل، ما Start Command را تغییر می‌دهیم
