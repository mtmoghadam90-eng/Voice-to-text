import os
import json
import requests
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from threading import Thread

# --- تنظیمات اصلی از Environment Variables ---
# توکن‌ها را دیگر مستقیم در کد وارد نمی‌کنیم
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SPEECHMATICS_API_KEY = os.environ.get("SPEECHMATICS_API_KEY")

SPEECHMATICS_URL = "https://asr.api.speechmatics.com/v2/jobs/"

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """فایل صوتی را پردازش می‌کند."""
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
                time.sleep(10)
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

def run_bot():
    """ربات تلگرام را اجرا می‌کند."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    print("Bot is running in polling mode...")
    application.run_polling()

# این بخش برای زنده نگه داشتن سرویس در Render است
if __name__ == "__main__":
    # اجرای ربات در یک ترد جداگانه
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    # این بخش یک سرور وب ساده ایجاد می‌کند تا Render سرویس را فعال نگه دارد
    # شما نیازی به درک کامل این قسمت ندارید
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Bot is running!')

    print("Starting dummy HTTP server...")
    httpd = HTTPServer(('0.0.0.0', 8080), SimpleHTTPRequestHandler)
    httpd.serve_forever()
