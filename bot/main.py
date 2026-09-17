import os

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database import initialize_database


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
initialize_database()

MAIN_KEYBOARD = [
    ["📖 القرآن والثقافة", "📚 الملازم"],
    ["🎧 المحاضرات", "ℹ️ عن البوت"],
]
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        MAIN_KEYBOARD,
        resize_keyboard=True,
        is_persistent=True,
    )

    await update.message.reply_text(
        "🌿 أهلاً بك في بوت هدى للناس\n\n"
        "اختر من القائمة:",
        reply_markup=keyboard,
    )
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        f"🔎 Telegram ID الخاص بك هو:\n\n{user_id}\n\n"
        "قارن هذا الرقم مع الرقم الموجود في ADMIN_ID داخل GitHub."
    )

    if str(user_id) != str(ADMIN_ID):
        await update.message.reply_text("❌ ليس لديك صلاحية الدخول.")
        return

    await update.message.reply_text(
        "⚙️ لوحة تحكم المشرف\n\n"
        "اختر العملية التي تريد تنفيذها:"
    )

    await update.message.reply_text(
        "🌿 أهلاً بك في بوت هدى للناس\n\n"
        "اختر من القائمة:",
        reply_markup=keyboard,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📖 القرآن والثقافة":
        await update.message.reply_text(
            "📖 القرآن والثقافة\n\n"
            "سيتم إضافة المحتوى هنا."
        )

    elif text == "📚 الملازم":
        await update.message.reply_text(
            "📚 الملازم\n\n"
            "سيتم إضافة الملازم هنا."
        )

    elif text == "🎧 المحاضرات":
        await update.message.reply_text(
            "🎧 المحاضرات\n\n"
            "سيتم إضافة المحاضرات هنا."
        )

    elif text == "ℹ️ عن البوت":
        await update.message.reply_text(
            "ℹ️ عن بوت هدى للناس\n\n"
            "منصة ثقافية قيد التطوير."
        )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN غير موجود")

    print("🚀 Huda People Bot is starting...", flush=True)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    from telegram.ext import MessageHandler, filters

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("✅ Bot is running...", flush=True)

    app.run_polling()


if __name__ == "__main__":
    main()
