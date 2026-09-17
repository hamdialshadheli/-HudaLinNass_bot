import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌿 أهلاً بك في بوت هدى للناس\n\n"
        "تم تشغيل البوت بنجاح ✅"
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN غير موجود")

    print("🚀 Huda People Bot is starting...", flush=True)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("✅ Bot is running...", flush=True)

    app.run_polling()


if __name__ == "__main__":
    main()
