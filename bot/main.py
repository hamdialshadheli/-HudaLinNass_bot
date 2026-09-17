import os

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from database import initialize_database, get_connection

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

    if str(user_id) != str(ADMIN_ID):
        await update.message.reply_text(
            "❌ ليس لديك صلاحية الدخول."
        )
        return

    keyboard = ReplyKeyboardMarkup(
        [
            ["➕ إضافة قائمة"],
            ["📋 إدارة القوائم"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

    await update.message.reply_text(
        "⚙️ لوحة تحكم المشرف\n\n"
        "اختر العملية التي تريد تنفيذها:",
        reply_markup=keyboard,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # ==========================================
    # إضافة قائمة رئيسية
    # ==========================================

    if text == "➕ إضافة قائمة":
        context.user_data["adding_menu"] = True

        await update.message.reply_text(
            "➕ إضافة قائمة\n\n"
            "أرسل اسم القائمة الجديدة:"
        )
        return

    # ==========================================
    # حفظ القائمة الجديدة
    # ==========================================

    if context.user_data.get("adding_menu"):

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO menus (name, parent_id, sort_order)
            VALUES (?, ?, ?)
            """,
            (text, None, 0),
        )

        connection.commit()
        connection.close()

        context.user_data["adding_menu"] = False

        await update.message.reply_text(
            "✅ تم إنشاء القائمة بنجاح\n\n"
            f"📁 {text}"
        )
        return

    # ==========================================
    # إدارة القوائم
    # ==========================================

    if text == "📋 إدارة القوائم":

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name
            FROM menus
            WHERE parent_id IS NULL
            ORDER BY sort_order, id
            """
        )

        menus = cursor.fetchall()
        connection.close()

        if not menus:
            await update.message.reply_text(
                "📋 لا توجد قوائم منشأة حتى الآن."
            )
            return

        keyboard = []

        for menu in menus:
            keyboard.append(
                [f"📁 {menu['name']}"]
            )

        await update.message.reply_text(
            "📋 القوائم الرئيسية:\n\n"
            "اختر القائمة التي تريد إدارتها:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                is_persistent=True,
            ),
        )

        return

    # ==========================================
    # فتح القائمة وإظهار خيارات إدارتها
    # ==========================================

    if text.startswith("📁 "):

        menu_name = text[2:].strip()

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name
            FROM menus
            WHERE name = ? AND parent_id IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (menu_name,),
        )

        menu = cursor.fetchone()
        connection.close()

        if not menu:
            await update.message.reply_text(
                "❌ لم يتم العثور على هذه القائمة."
            )
            return

        context.user_data["current_menu_id"] = menu["id"]

        keyboard = ReplyKeyboardMarkup(
            [
                ["➕ إضافة فرع"],
                ["📝 إضافة نص"],
                ["🖼️ إضافة صورة"],
                ["🎬 إضافة فيديو"],
                ["◀️ رجوع"],
            ],
            resize_keyboard=True,
            is_persistent=True,
        )

        await update.message.reply_text(
            f"📁 إدارة القائمة: {menu['name']}\n\n"
            "اختر العملية التي تريد تنفيذها:",
            reply_markup=keyboard,
        )

        return

    # ==========================================
    # رجوع
    # ==========================================

    if text == "◀️ رجوع":

        keyboard = ReplyKeyboardMarkup(
            [
                ["➕ إضافة قائمة"],
                ["📋 إدارة القوائم"],
            ],
            resize_keyboard=True,
            is_persistent=True,
        )

        await update.message.reply_text(
            "⚙️ لوحة تحكم المشرف\n\n"
            "اختر العملية التي تريد تنفيذها:",
            reply_markup=keyboard,
        )

        context.user_data.pop("current_menu_id", None)

        return

    # ==========================================
    # القوائم العامة للبوت
    # ==========================================

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

    if not ADMIN_ID:
        raise ValueError("ADMIN_ID غير موجود")

    print(
        "🚀 Huda People Bot is starting...",
        flush=True,
    )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("admin", admin)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    print(
        "✅ Bot is running...",
        flush=True
    )

    app.run_polling()


if __name__ == "__main__":
    main()
