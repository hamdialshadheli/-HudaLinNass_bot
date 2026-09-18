import os

from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot.database import (
    initialize_database,
    register_user,
    is_admin,
    get_connection,
)

from bot.keyboards import (
    user_keyboard,
    admin_keyboard,
)

from bot.handlers.menus import (
    show_menu,
    create_root_menu,
    create_child_menu,
    go_back_one_level,
)

from bot.handlers.content import (
    start_add_content,
    select_content_type,
    receive_content_title,
    receive_text_content,
    receive_link_content,
    receive_photo_content,
    receive_video_content,
    receive_audio_content,
    receive_document_content,
    list_editable_content,
    list_deletable_content,
    handle_content_callback,
    save_edit_value,
    confirm_delete_content,
    open_content_by_title,
    send_content,
)

from bot.handlers.admin import (
    show_admins,
    start_add_admin,
    receive_admin_id,
    start_remove_admin,
    receive_remove_admin_id,
    show_stats,
)

from bot.handlers.media_groups import (
    start_media_group,
    receive_group_title,
    receive_group_description,
    finish_media_group,
    open_media_group,
)


# ============================================================
# إعدادات البوت
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في GitHub Secrets"
    )

if not ADMIN_ID:
    raise RuntimeError(
        "ADMIN_ID غير موجود في GitHub Secrets"
    )


# ============================================================
# الواجهة الرئيسية للمستخدم
# ============================================================

async def show_public_home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    admin_status = is_admin(user_id)

    keyboard = user_keyboard(
        is_admin_user=admin_status
    )

    print(
        "========================================",
        flush=True
    )

    print(
        "PUBLIC HOME CALLED",
        flush=True
    )

    print(
        "USER ID:",
        user_id,
        flush=True
    )

    print(
        "IS ADMIN:",
        admin_status,
        flush=True
    )

    print(
        "USER KEYBOARD RUNTIME:",
        keyboard.keyboard,
        flush=True
    )

    print(
        "========================================",
        flush=True
    )

    # إزالة لوحة المفاتيح القديمة
    await update.message.reply_text(
        "🔄",
        reply_markup=ReplyKeyboardRemove()
    )

    # ========================================================
    # لوحة اختبار مؤقتة
    # ========================================================

    test_keyboard = ReplyKeyboardMarkup(
        [
            ["🧪 زر اختبار 1"],
            ["🧪 زر اختبار 2"],
            ["🧪 زر اختبار 3"],
            ["🧪 زر اختبار 4"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )

    await update.message.reply_text(
        "🌿 مرحباً بك في هدى للناس\n\n"
        "اختبار لوحة المفاتيح",
        reply_markup=test_keyboard
    )


# ============================================================
# أمر START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or ""

    print(
        "========================================",
        flush=True
    )

    print(
        "START COMMAND RECEIVED",
        flush=True
    )

    print(
        "USER ID:",
        user_id,
        flush=True
    )

    print(
        "USER NAME:",
        user_name,
        flush=True
    )

    print(
        "========================================",
        flush=True
    )

    register_user(
        update.effective_user
    )

    context.user_data.clear()

    # رسالة اختبار مؤقتة
    await update.message.reply_text(
        "🧪 TEST VERSION\n\n"
        "إذا ظهرت لك هذه الرسالة، فهذا يعني أن "
        "نسخة البوت التي تعمل من GitHub هي التي "
        "استقبلت أمر /start."
    )

    await show_public_home(
        update,
        context
    )


# ============================================================
# لوحة الإدارة
# ============================================================

async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await update.message.reply_text(
            "❌ ليس لديك صلاحية الدخول إلى لوحة الإدارة."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ لوحة إدارة البوت",
        reply_markup=admin_keyboard()
    )


# ============================================================
# معالجة الرسائل النصية
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    text = update.message.text or ""

    user_id = update.effective_user.id

    register_user(
        update.effective_user
    )

    # ========================================================
    # الإدارة
    # ========================================================

    if text == "⚙️ الإدارة":

        if is_admin(user_id):

            await admin(
                update,
                context
            )

        else:

            await update.message.reply_text(
                "❌ ليس لديك صلاحية الإدارة."
            )

        return

    # ========================================================
    # واجهة المستخدم
    # ========================================================

    if text == "👤 واجهة المستخدم":

        context.user_data.clear()

        await show_public_home(
            update,
            context
        )

        return

    # ========================================================
    # القائمة الرئيسية
    # ========================================================

    if text == "🏠 القائمة الرئيسية":

        context.user_data.clear()

        await show_public_home(
            update,
            context
        )

        return

    # ========================================================
    # رجوع
    # ========================================================

    if text == "◀️ رجوع":

        await go_back_one_level(
            update,
            context
        )

        return

    # ========================================================
    # إنشاء قائمة رئيسية
    # ========================================================

    if text == "➕ إنشاء قائمة":

        if not is_admin(user_id):
            return

        context.user_data["state"] = (
            "creating_root_menu"
        )

        await update.message.reply_text(
            "✏️ أرسل اسم القائمة الرئيسية الجديدة:"
        )

        return

    # ========================================================
    # إدارة القوائم
    # ========================================================

    if text in (
        "📂 إدارة القوائم",
        "📋 إدارة القوائم",
    ):

        if not is_admin(user_id):
            return

        connection = get_connection()

        roots = connection.execute("""
            SELECT id, name
            FROM menus
            WHERE parent_id IS NULL
            ORDER BY
                CASE
                    WHEN display_order IS NULL THEN 1
                    ELSE 0
                END,
                display_order,
                id
        """).fetchall()

        connection.close()

        if not roots:

            await update.message.reply_text(
                "📭 لا توجد قوائم رئيسية حالياً."
            )

            return

        keyboard = []

        for root in roots:

            keyboard.append([
                f"📂 {root['name']}"
            ])

        keyboard.append([
            "◀️ رجوع"
        ])

        context.user_data["state"] = (
            "managing_root_menus"
        )

        await update.message.reply_text(
            "📋 القوائم الرئيسية:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )
        )

        return

    # ========================================================
    # إضافة فرع
    # ========================================================

    if text == "➕ إضافة فرع":

        if not is_admin(user_id):
            return

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not current_menu_id:

            await update.message.reply_text(
                "❌ يجب الدخول إلى قائمة أولاً."
            )

            return

        context.user_data["state"] = (
            "creating_child_menu"
        )

        await update.message.reply_text(
            "✏️ أرسل اسم الفرع الجديد:"
        )

        return

    # ========================================================
    # إضافة محتوى
    # ========================================================

    if text == "➕ إضافة محتوى":

        if not is_admin(user_id):
            return

        await start_add_content(
            update,
            context
        )

        return

    # ========================================================
    # أنواع المحتوى
    # ========================================================

    if text in (
        "📝 نص",
        "🖼️ صورة",
        "🎥 فيديو",
        "🎧 صوت",
        "📄 ملف",
        "🔗 رابط",
        "🖼️🎥🎧 مجموعة وسائط",
    ):

        if not is_admin(user_id):
            return

        await select_content_type(
            update,
            context,
            text
        )

        return

    # ========================================================
    # تعديل المحتوى
    # ========================================================

    if text == "✏️ تعديل المحتوى":

        if not is_admin(user_id):
            return

        await list_editable_content(
            update,
            context
        )

        return

    # ========================================================
    # حذف المحتوى
    # ========================================================

    if text == "🗑️ حذف المحتوى":

        if not is_admin(user_id):
            return

        await list_deletable_content(
            update,
            context
        )

        return

    # ========================================================
    # ترتيب العناصر
    # ========================================================

    if text == "↕️ ترتيب العناصر":

        if not is_admin(user_id):
            return

        await update.message.reply_text(
            "↕️ سيتم اختبار ترتيب العناصر "
            "بعد التأكد من عمل الواجهات."
        )

        return

    # ========================================================
    # المشرفون
    # ========================================================

    if text == "👥 المشرفون":

        if not is_admin(user_id):
            return

        await show_admins(
            update,
            context
        )

        return

    # ========================================================
    # الإحصائيات
    # ========================================================

    if text == "📊 الإحصائيات":

        if not is_admin(user_id):
            return

        await show_stats(
            update,
            context
        )

        return

    # ========================================================
    # إضافة مشرف
    # ========================================================

    if text == "➕ إضافة مشرف":

        if not is_admin(user_id):
            return

        await start_add_admin(
            update,
            context
        )

        return

    # ========================================================
    # حذف مشرف
    # ========================================================

    if text == "🗑️ حذف مشرف":

        if not is_admin(user_id):
            return

        await start_remove_admin(
            update,
            context
        )

        return

    # ========================================================
    # إلغاء
    # ========================================================

    if text == "❌ إلغاء":

        context.user_data.clear()

        await admin(
            update,
            context
        )

        return

    # ========================================================
    # قراءة الحالة الحالية
    # ========================================================

    state = context.user_data.get(
        "state"
    )

    # ========================================================
    # إنشاء قائمة رئيسية
    # ========================================================

    if state == "creating_root_menu":

        await create_root_menu(
            update,
            context,
            text
        )

        context.user_data.pop(
            "state",
            None
        )

        return

    # ========================================================
    # إنشاء فرع
    # ========================================================

    if state == "creating_child_menu":

        parent_id = context.user_data.get(
            "current_menu_id"
        )

        await create_child_menu(
            update,
            context,
            parent_id,
            text
        )

        context.user_data.pop(
            "state",
            None
        )

        return

    # ========================================================
    # عنوان المحتوى
    # ========================================================

    if state == "content_title":

        await receive_content_title(
            update,
            context
        )

        return

    # ========================================================
    # محتوى نصي
    # ========================================================

    if state == "content_text":

        await receive_text_content(
            update,
            context
        )

        return

    # ========================================================
    # رابط
    # ========================================================

    if state == "content_link":

        await receive_link_content(
            update,
            context
        )

        return

    # ========================================================
    # تعديل المحتوى
    # ========================================================

    if state == "editing_content":

        await save_edit_value(
            update,
            context
        )

        return

    # ========================================================
    # إضافة مشرف
    # ========================================================

    if state == "adding_admin":

        await receive_admin_id(
            update,
            context
        )

        return

    # ========================================================
    # حذف مشرف
    # ========================================================

    if state == "removing_admin":

        await receive_remove_admin_id(
            update,
            context
        )

        return

    # ========================================================
    # عنوان مجموعة الوسائط
    # ========================================================

    if state == "media_group_title":

        await receive_group_title(
            update,
            context
        )

        return

    # ========================================================
    # وصف مجموعة الوسائط
    # ========================================================

    if state == "media_group_description":

        await receive_group_description(
            update,
            context
        )

        return

    # ========================================================
    # فتح قائمة
    # ========================================================

    if text.startswith("📂 "):

        menu_name = text[3:].strip()

        connection = get_connection()

        menu = connection.execute("""
            SELECT id
            FROM menus
            WHERE name = ?
            LIMIT 1
        """, (menu_name,)).fetchone()

        connection.close()

        if menu:

            await show_menu(
                update,
                context,
                menu["id"]
            )

            return

    # ========================================================
    # فتح المحتوى
    # ========================================================

    await open_content_by_title(
        update,
        context,
        text
    )


# ============================================================
# استقبال الصور
# ============================================================

async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    state = context.user_data.get(
        "state"
    )

    if state == "content_photo":

        await receive_photo_content(
            update,
            context
        )

        return


# ============================================================
# استقبال الفيديو
# ============================================================

async def handle_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    state = context.user_data.get(
        "state"
    )

    if state == "content_video":

        await receive_video_content(
            update,
            context
        )

        return


# ============================================================
# استقبال الصوت
# ============================================================

async def handle_audio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    state = context.user_data.get(
        "state"
    )

    if state == "content_audio":

        await receive_audio_content(
            update,
            context
        )

        return


# ============================================================
# استقبال الملفات
# ============================================================

async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    state = context.user_data.get(
        "state"
    )

    if state == "content_document":

        await receive_document_content(
            update,
            context
        )

        return


# ============================================================
# تشغيل البوت
# ============================================================

def main():

    print(
        "========================================",
        flush=True
    )

    print(
        "Huda People Bot is starting...",
        flush=True
    )

    print(
        "========================================",
        flush=True
    )

    initialize_database()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ========================================================
    # الأوامر
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )

    # ========================================================
    # الصور
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo
        )
    )

    # ========================================================
    # الفيديو
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.VIDEO,
            handle_video
        )
    )

    # ========================================================
    # الصوت
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.AUDIO,
            handle_audio
        )
    )

    # ========================================================
    # الملفات
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_document
        )
    )

    # ========================================================
    # الرسائل النصية
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print(
        "Huda People Bot is running...",
        flush=True
    )

    application.run_polling(
        drop_pending_updates=False
    )


# ============================================================
# نقطة تشغيل البرنامج
# ============================================================

if __name__ == "__main__":
    main()
