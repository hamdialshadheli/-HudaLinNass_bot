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


# =========================================================
# أدوات مساعدة
# =========================================================

def admin_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["➕ إضافة قائمة"],
            ["📋 إدارة القوائم"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def menu_keyboard(menu_id):
    connection = get_connection()
    cursor = connection.cursor()

    # الفروع
    cursor.execute(
        """
        SELECT id, name
        FROM menus
        WHERE parent_id = ?
        ORDER BY sort_order, id
        """,
        (menu_id,),
    )

    branches = cursor.fetchall()

    # المحتوى
    cursor.execute(
        """
        SELECT id, title, content_type
        FROM contents
        WHERE menu_id = ?
        ORDER BY sort_order, id
        """,
        (menu_id,),
    )

    contents = cursor.fetchall()

    connection.close()

    keyboard = []

    # الفروع
    for branch in branches:
        keyboard.append(
            [f"📁 {branch['name']}"]
        )

    # المحتوى
    for content in contents:

        if content["content_type"] == "text":
            icon = "📝"

        elif content["content_type"] == "photo":
            icon = "🖼️"

        elif content["content_type"] == "video":
            icon = "🎬"

        else:
            icon = "📄"

        keyboard.append(
            [f"{icon} {content['title']}"]
        )

    # خيارات الإدارة
    keyboard.append(["➕ إضافة فرع"])
    keyboard.append(["📝 إضافة نص"])
    keyboard.append(["🖼️ إضافة صورة"])
    keyboard.append(["🎬 إضافة فيديو"])
    keyboard.append(["◀️ رجوع"])

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )


async def show_menu(
    update,
    context,
    menu_id,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, name, parent_id
        FROM menus
        WHERE id = ?
        """,
        (menu_id,),
    )

    menu = cursor.fetchone()

    connection.close()

    if not menu:
        await update.message.reply_text(
            "❌ لم يتم العثور على القائمة."
        )
        return

    # حفظ القائمة الحالية
    context.user_data["current_menu_id"] = menu["id"]

    # حفظ اسم القائمة
    context.user_data["current_menu_name"] = menu["name"]

    await update.message.reply_text(
        f"📁 {menu['name']}\n\n"
        "اختر من الفروع أو المحتوى:",
        reply_markup=menu_keyboard(menu["id"]),
    )


# =========================================================
# /start
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # تنظيف حالة الإدارة
    context.user_data.clear()

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


# =========================================================
# /admin
# =========================================================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if str(user_id) != str(ADMIN_ID):

        await update.message.reply_text(
            "❌ ليس لديك صلاحية الدخول."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ لوحة تحكم المشرف\n\n"
        "اختر العملية التي تريد تنفيذها:",
        reply_markup=admin_keyboard(),
    )


# =========================================================
# معالجة الرسائل
# =========================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    # =====================================================
    # إلغاء أي عملية عند الضغط على رجوع
    # =====================================================

    if text == "◀️ رجوع":

        # إلغاء عمليات الإدخال
        context.user_data.pop("adding_menu", None)
        context.user_data.pop("adding_branch", None)
        context.user_data.pop("adding_text", None)
        context.user_data.pop("waiting_text_content", None)
        context.user_data.pop("adding_photo", None)
        context.user_data.pop("waiting_photo", None)
        context.user_data.pop("adding_video", None)
        context.user_data.pop("waiting_video", None)
        context.user_data.pop("content_title", None)

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        # إذا كنا داخل قائمة
        if current_menu_id:

            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT parent_id
                FROM menus
                WHERE id = ?
                """,
                (current_menu_id,),
            )

            current_menu = cursor.fetchone()

            connection.close()

            if current_menu:

                parent_id = current_menu["parent_id"]

                # إذا يوجد أب، نرجع إليه
                if parent_id:

                    await show_menu(
                        update,
                        context,
                        parent_id,
                    )

                    return

        # إذا لا يوجد أب، نرجع للوحة الإدارة
        context.user_data.clear()

        await update.message.reply_text(
            "⚙️ لوحة تحكم المشرف\n\n"
            "اختر العملية التي تريد تنفيذها:",
            reply_markup=admin_keyboard(),
        )

        return

    # =====================================================
    # إضافة قائمة رئيسية
    # =====================================================

    if text == "➕ إضافة قائمة":

        context.user_data.clear()

        context.user_data["adding_menu"] = True

        await update.message.reply_text(
            "➕ إضافة قائمة\n\n"
            "أرسل اسم القائمة الجديدة:"
        )

        return

    # =====================================================
    # حفظ القائمة الرئيسية
    # =====================================================

    if context.user_data.get("adding_menu"):

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO menus
            (name, parent_id, sort_order)
            VALUES (?, ?, ?)
            """,
            (text, None, 0),
        )

        menu_id = cursor.lastrowid

        connection.commit()
        connection.close()

        context.user_data["adding_menu"] = False
        context.user_data["current_menu_id"] = menu_id

        await update.message.reply_text(
            "✅ تم إنشاء القائمة بنجاح\n\n"
            f"📁 {text}"
        )

        # تحديث القائمة مباشرة
        await show_menu(
            update,
            context,
            menu_id,
        )

        return

    # =====================================================
    # إدارة القوائم
    # =====================================================

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
                "📋 لا توجد قوائم منشأة حتى الآن.",
                reply_markup=admin_keyboard(),
            )

            return

        keyboard = []

        for menu in menus:
            keyboard.append(
                [f"📁 {menu['name']}"]
            )

        keyboard.append(["◀️ رجوع"])

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

    # =====================================================
    # إضافة فرع
    # =====================================================

    if text == "➕ إضافة فرع":

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not current_menu_id:

            await update.message.reply_text(
                "❌ لم يتم تحديد القائمة الحالية."
            )

            return

        # إلغاء الحالات السابقة
        context.user_data.pop("adding_text", None)
        context.user_data.pop("waiting_text_content", None)
        context.user_data.pop("adding_photo", None)
        context.user_data.pop("waiting_photo", None)
        context.user_data.pop("adding_video", None)
        context.user_data.pop("waiting_video", None)

        context.user_data["adding_branch"] = True

        await update.message.reply_text(
            "➕ إضافة فرع\n\n"
            "أرسل اسم الفرع الجديد:\n\n"
            "أو اضغط ◀️ رجوع للإلغاء."
        )

        return

    # =====================================================
    # حفظ الفرع
    # =====================================================

    if context.user_data.get("adding_branch"):

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO menus
            (name, parent_id, sort_order)
            VALUES (?, ?, ?)
            """,
            (text, current_menu_id, 0),
        )

        new_branch_id = cursor.lastrowid

        connection.commit()
        connection.close()

        context.user_data["adding_branch"] = False

        await update.message.reply_text(
            "✅ تم إنشاء الفرع بنجاح\n\n"
            f"📁 {text}"
        )

        # تحديث القائمة مباشرة
        await show_menu(
            update,
            context,
            current_menu_id,
        )

        return

    # =====================================================
    # إضافة نص
    # =====================================================

    if text == "📝 إضافة نص":

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not current_menu_id:

            await update.message.reply_text(
                "❌ لم يتم تحديد القائمة الحالية."
            )

            return

        context.user_data["adding_text"] = True

        await update.message.reply_text(
            "📝 إضافة نص\n\n"
            "أرسل عنوان النص:\n\n"
            "أو اضغط ◀️ رجوع للإلغاء."
        )

        return

    # =====================================================
    # عنوان النص
    # =====================================================

    if context.user_data.get("adding_text"):

        context.user_data["content_title"] = text
        context.user_data["adding_text"] = False
        context.user_data["waiting_text_content"] = True

        await update.message.reply_text(
            "✍️ الآن أرسل محتوى النص:\n\n"
            "أو اضغط ◀️ رجوع للإلغاء."
        )

        return

    # =====================================================
    # حفظ النص
    # =====================================================

    if context.user_data.get("waiting_text_content"):

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "content_title"
        )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO contents
            (
                menu_id,
                title,
                content_type,
                text_content,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                current_menu_id,
                title,
                "text",
                text,
                0,
            ),
        )

        connection.commit()
        connection.close()

        context.user_data.pop(
            "content_title",
            None
        )

        context.user_data["waiting_text_content"] = False

        await update.message.reply_text(
            "✅ تم حفظ النص بنجاح\n\n"
            f"📝 {title}"
        )

        # تحديث القائمة مباشرة
        await show_menu(
            update,
            context,
            current_menu_id,
        )

        return

    # =====================================================
    # إضافة صورة
    # =====================================================

    if text == "🖼️ إضافة صورة":

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not current_menu_id:

            await update.message.reply_text(
                "❌ لم يتم تحديد القائمة الحالية."
            )

            return

        context.user_data["adding_photo"] = True

        await update.message.reply_text(
            "🖼️ إضافة صورة\n\n"
            "أرسل عنوان الصورة:\n\n"
            "أو اضغط ◀️ رجوع للإلغاء."
        )

        return

    # =====================================================
    # عنوان الصورة
    # =====================================================

    if context.user_data.get("adding_photo"):

        context.user_data["content_title"] = text
        context.user_data["adding_photo"] = False
        context.user_data["waiting_photo"] = True

        await update.message.reply_text(
            "📷 الآن أرسل الصورة:\n\n"
            "أو اضغط ◀️ رجوع للإلغاء."
        )

        return

    # =====================================================
    # إضافة فيديو
    # =====================================================

    if text == "🎬 إضافة فيديو":

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not current_menu_id:

            await update.message.reply_text(
                "❌ لم يتم تحديد القائمة الحالية."
            )

            return

        context.user_data["adding_video"] = True

        await update.message.reply_text(
            "🎬 إضافة فيديو\n\n"
            "أرسل عنوان الفيديو:\n\n"
            "أو اضغط ◀️ رجوع للإلغاء."
        )

        return

    # =====================================================
    # عنوان الفيديو
    # =====================================================

    if context.user_data.get("adding_video"):

        context.user_data["content_title"] = text
        context.user_data["adding_video"] = False
        context.user_data["waiting_video"] = True

        await update.message.reply_text(
            "🎥 الآن أرسل الفيديو:\n\n"
            "أو اضغط ◀️ رجوع للإلغاء."
        )

        return

    # =====================================================
    # استقبال الصورة
    # =====================================================

    if context.user_data.get("waiting_photo"):

        if not update.message.photo:

            await update.message.reply_text(
                "❌ أرسل صورة من فضلك.\n\n"
                "أو اضغط ◀️ رجوع للإلغاء."
            )

            return

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "content_title"
        )

        file_id = update.message.photo[-1].file_id
        caption = update.message.caption

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO contents
            (
                menu_id,
                title,
                content_type,
                file_id,
                caption,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                current_menu_id,
                title,
                "photo",
                file_id,
                caption,
                0,
            ),
        )

        connection.commit()
        connection.close()

        context.user_data.pop(
            "content_title",
            None
        )

        context.user_data["waiting_photo"] = False

        await update.message.reply_text(
            "✅ تم حفظ الصورة بنجاح\n\n"
            f"🖼️ {title}"
        )

        # تحديث القائمة مباشرة
        await show_menu(
            update,
            context,
            current_menu_id,
        )

        return

    # =====================================================
    # استقبال الفيديو
    # =====================================================

    if context.user_data.get("waiting_video"):

        if not update.message.video:

            await update.message.reply_text(
                "❌ أرسل فيديو من فضلك.\n\n"
                "أو اضغط ◀️ رجوع للإلغاء."
            )

            return

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "content_title"
        )

        file_id = update.message.video.file_id
        caption = update.message.caption

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO contents
            (
                menu_id,
                title,
                content_type,
                file_id,
                caption,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                current_menu_id,
                title,
                "video",
                file_id,
                caption,
                0,
            ),
        )

        connection.commit()
        connection.close()

        context.user_data.pop(
            "content_title",
            None
        )

        context.user_data["waiting_video"] = False

        await update.message.reply_text(
            "✅ تم حفظ الفيديو بنجاح\n\n"
            f"🎬 {title}"
        )

        # تحديث القائمة مباشرة
        await show_menu(
            update,
            context,
            current_menu_id,
        )

        return

    # =====================================================
    # فتح قائمة / فرع
    # =====================================================

    if text.startswith("📁 "):

        menu_name = text[2:].strip()

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM menus
            WHERE name = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (menu_name,),
        )

        menu = cursor.fetchone()

        connection.close()

        if not menu:

            await update.message.reply_text(
                "❌ لم يتم العثور على القائمة."
            )

            return

        await show_menu(
            update,
            context,
            menu["id"],
        )

        return

    # =====================================================
    # فتح المحتوى
    # =====================================================

    if (
        text.startswith("📝 ")
        or text.startswith("🖼️ ")
        or text.startswith("🎬 ")
    ):

        title = text[2:].strip()

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM contents
            WHERE title = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (title,),
        )

        content = cursor.fetchone()

        connection.close()

        if not content:

            await update.message.reply_text(
                "❌ لم يتم العثور على المحتوى."
            )

            return

        if content["content_type"] == "text":

            await update.message.reply_text(
                f"📝 {content['title']}\n\n"
                f"{content['text_content']}"
            )

        elif content["content_type"] == "photo":

            await update.message.reply_photo(
                photo=content["file_id"],
                caption=content["caption"] or "",
            )

        elif content["content_type"] == "video":

            await update.message.reply_video(
                video=content["file_id"],
                caption=content["caption"] or "",
            )

        return

    # =====================================================
    # القوائم العامة
    # =====================================================

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


# =========================================================
# تشغيل البوت
# =========================================================

def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN غير موجود"
        )

    if not ADMIN_ID:
        raise ValueError(
            "ADMIN_ID غير موجود"
        )

    print(
        "🚀 Huda People Bot is starting...",
        flush=True,
    )

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )

    # الرسائل النصية
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    # الصور والفيديوهات
    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.VIDEO,
            handle_message,
        )
    )

    print(
        "✅ Bot is running...",
        flush=True,
    )

    app.run_polling()


if __name__ == "__main__":
    main()
