import os
import json
import requests
import time
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- تنظیمات اصلی از Environment Variables ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SPEECHMATICS_API_KEY = os.environ.get("SPEECHMATICS_API_KEY")
SPEECHMATICS_URL = "https://asr.api.speechmatics.com/v2/jobs/"

# این تابع اصلی ربات است و بدون تغییر باقی می‌ماند
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                await asyncio.sleep(10) # استفاده از asyncio.sleep به جای time.sleep
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

# --- بخش اصلی برنامه (کاملاً تغییر یافته) ---
async def main():
    """ربات را راه‌اندازی و اجرا می‌کند."""
    
    # ساخت اپلیکیشن ربات
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # اضافه کردن handler برای پیام‌های صوتی
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))

    # این بخش ربات را به صورت ناهمزمان اجرا می‌کند
    # و دیگر نیازی به ترد و وب سرور جداگانه نیست
    print("Bot is starting in async mode...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # این حلقه بی‌نهایت، اسکریپت را زنده نگه می‌دارد
    while True:
        await asyncio.sleep(3600) # هر یک ساعت یک بار بیدار می‌شود تا سرویس خاموش نشود

if __name__ == "__main__":
    # اجرای حلقه asyncio
    asyncio.run(main())

