import os

from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from bot.database import (
    initialize_database,
    register_user,
    is_admin,
    add_admin,
    get_connection,
)

from bot.keyboards import (
    admin_keyboard,
    menu_management_keyboard,
    content_type_keyboard,
    cancel_keyboard,
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
    strip_content_icon,
)

from bot.handlers.admin import (
    show_stats,
    show_admins,
)


# ==========================================
# تحميل الإعدادات
# ==========================================

load_dotenv()

BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)

ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "0",
    )
)


# ==========================================
# القائمة الرئيسية للمستخدم
# ==========================================

async def show_public_home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    connection = get_connection()

    roots = connection.execute(
        """
        SELECT
            id,
            name
        FROM menus
        WHERE parent_id IS NULL
        ORDER BY display_order, id
        """
    ).fetchall()

    connection.close()

    keyboard = []

    for root in roots:

        keyboard.append([
            f"📂 {root['name']}"
        ])

    keyboard.append([
        "⚙️ الإدارة"
    ])

    await update.message.reply_text(
        "🌿 مرحباً بك في هدى للناس",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


# ==========================================
# /start
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    register_user(
        update.effective_user
    )

    await show_public_home(
        update,
        context,
    )


# ==========================================
# /admin
# ==========================================

async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    register_user(
        update.effective_user
    )

    if not is_admin(
        update.effective_user.id
    ):

        await update.message.reply_text(
            "⛔ ليس لديك صلاحية المشرف."
        )

        return

    await update.message.reply_text(
        "⚙️ لوحة إدارة البوت",
        reply_markup=admin_keyboard(),
    )


# ==========================================
# فتح قائمة رئيسية
# ==========================================

async def open_root_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):

    menu_name = text[
        len("📂 "):
    ].strip()

    connection = get_connection()

    menu = connection.execute(
        """
        SELECT *
        FROM menus
        WHERE name = ?
        AND parent_id IS NULL
        LIMIT 1
        """,
        (menu_name,),
    ).fetchone()

    connection.close()

    if not menu:
        return

    await show_menu(
        update,
        context,
        menu["id"],
    )


# ==========================================
# فتح فرع داخل القائمة الحالية
# ==========================================

async def open_child_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):

    menu_name = text[
        len("📂 "):
    ].strip()

    current_menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not current_menu_id:
        return

    connection = get_connection()

    menu = connection.execute(
        """
        SELECT *
        FROM menus
        WHERE name = ?
        AND parent_id = ?
        LIMIT 1
        """,
        (
            menu_name,
            current_menu_id,
        ),
    ).fetchone()

    connection.close()

    if not menu:
        return

    await show_menu(
        update,
        context,
        menu["id"],
    )


# ==========================================
# إدارة القوائم
# ==========================================

async def manage_menus(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    connection = get_connection()

    roots = connection.execute(
        """
        SELECT
            id,
            name
        FROM menus
        WHERE parent_id IS NULL
        ORDER BY display_order, id
        """
    ).fetchall()

    connection.close()

    if not roots:

        await update.message.reply_text(
            "ℹ️ لا توجد قوائم حاليًا.",
            reply_markup=admin_keyboard(),
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

    await update.message.reply_text(
        "📋 اختر القائمة التي تريد إدارتها:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


# ==========================================
# التعامل مع النصوص
# ==========================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    register_user(
        update.effective_user
    )

    text = (
        update.message.text
        or ""
    ).strip()

    user_id = update.effective_user.id

    # ======================================
    # إلغاء
    # ======================================

    if text == "❌ إلغاء":

        context.user_data.clear()

        if is_admin(user_id):

            await update.message.reply_text(
                "❌ تم إلغاء العملية.",
                reply_markup=admin_keyboard(),
            )

        else:

            await show_public_home(
                update,
                context,
            )

        return

    # ======================================
    # الرجوع
    # ======================================

    if text == "◀️ رجوع":

        context.user_data.pop(
            "waiting_for_content_title",
            None,
        )

        context.user_data.pop(
            "waiting_for_content_value",
            None,
        )

        context.user_data.pop(
            "waiting_for_edit_value",
            None,
        )

        await go_back_one_level(
            update,
            context,
        )

        return

    # ======================================
    # الإدارة
    # ======================================

    if text == "⚙️ الإدارة":

        await admin(
            update,
            context,
        )

        return

    # ======================================
    # القائمة الرئيسية
    # ======================================

    if text == "🏠 القائمة الرئيسية":

        context.user_data.clear()

        await admin(
            update,
            context,
        )

        return

    # ======================================
    # المستخدم العادي
    # ======================================

    if not is_admin(user_id):

        if text.startswith("📂 "):

            current_menu_id = context.user_data.get(
                "current_menu_id"
            )

            if current_menu_id:

                await open_child_menu(
                    update,
                    context,
                    text,
                )

            else:

                await open_root_menu(
                    update,
                    context,
                    text,
                )

            return

        title = strip_content_icon(
            text
        )

        opened = await open_content_by_title(
            update,
            context,
            title,
        )

        if opened:
            return

        return

    # ======================================
    # إضافة قائمة رئيسية
    # ======================================

    if text == "➕ إضافة قائمة":

        context.user_data[
            "waiting_for_root_name"
        ] = True

        await update.message.reply_text(
            "📂 اكتب اسم القائمة الرئيسية:",
            reply_markup=cancel_keyboard(),
        )

        return

    # ======================================
    # إدارة القوائم
    # ======================================

    if text == "📋 إدارة القوائم":

        await manage_menus(
            update,
            context,
        )

        return

    # ======================================
    # إضافة فرع
    # ======================================

    if text == "➕ إضافة فرع":

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not current_menu_id:

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "waiting_for_branch_name"
        ] = True

        await update.message.reply_text(
            "📂 اكتب اسم الفرع:",
            reply_markup=cancel_keyboard(),
        )

        return

    # ======================================
    # إضافة محتوى
    # ======================================

    if text == "➕ إضافة محتوى":

        await start_add_content(
            update,
            context,
        )

        return

    # ======================================
    # أنواع المحتوى
    # ======================================

    content_types = {

        "📝 نص": "text",

        "🖼️ صورة": "photo",

        "🎥 فيديو": "video",

        "🎧 صوت": "audio",

        "📄 ملف": "document",

        "🔗 رابط": "link",
    }

    if text in content_types:

        await select_content_type(
            update,
            context,
            content_types[text],
        )

        return

    # ======================================
    # مجموعة الوسائط
    # ======================================

    if text == "🖼️🎥🎧 مجموعة وسائط":

        await update.message.reply_text(
            "🖼️🎥🎧 نظام مجموعات الوسائط سيكون "
            "في الخطوة التالية، بعد تثبيت "
            "نظام المحتوى الأساسي."
        )

        return

    # ======================================
    # تعديل المحتوى
    # ======================================

    if text == "✏️ تعديل المحتوى":

        await list_editable_content(
            update,
            context,
        )

        return

    # ======================================
    # حذف المحتوى
    # ======================================

    if text == "🗑️ حذف المحتوى":

        await list_deletable_content(
            update,
            context,
        )

        return

    # ======================================
    # ترتيب العناصر
    # ======================================

    if text == "↕️ ترتيب العناصر":

        await update.message.reply_text(
            "↕️ نظام ترتيب العناصر سنفعّله "
            "بعد تثبيت إدارة المحتوى."
        )

        return

    # ======================================
    # المشرفون
    # ======================================

    if text == "👥 المشرفون":

        await show_admins(
            update,
            context,
        )

        return

    # ======================================
    # الإحصائيات
    # ======================================

    if text == "📊 الإحصائيات":

        await show_stats(
            update,
            context,
        )

        return

    # ======================================
    # اسم القائمة الرئيسية
    # ======================================

    if context.user_data.get(
        "waiting_for_root_name"
    ):

        context.user_data.pop(
            "waiting_for_root_name",
            None,
        )

        await create_root_menu(
            update,
            context,
            text,
        )

        return

    # ======================================
    # اسم الفرع
    # ======================================

    if context.user_data.get(
        "waiting_for_branch_name"
    ):

        parent_id = context.user_data.get(
            "current_menu_id"
        )

        context.user_data.pop(
            "waiting_for_branch_name",
            None,
        )

        await create_child_menu(
            update,
            context,
            parent_id,
            text,
        )

        return

    # ======================================
    # عنوان المحتوى
    # ======================================

    if context.user_data.get(
        "waiting_for_content_title"
    ):

        await receive_content_title(
            update,
            context,
        )

        return

    # ======================================
    # قيمة النص أو الرابط
    # ======================================

    if context.user_data.get(
        "waiting_for_content_value"
    ):

        content_type = context.user_data.get(
            "new_content_type"
        )

        if content_type == "text":

            await receive_text_content(
                update,
                context,
            )

            return

        if content_type == "link":

            await receive_link_content(
                update,
                context,
            )

            return

    # ======================================
    # قيمة التعديل
    # ======================================

    if context.user_data.get(
        "waiting_for_edit_value"
    ):

        await save_edit_value(
            update,
            context,
        )

        return


# ==========================================
# التعامل مع الوسائط
# ==========================================

async def handle_media(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get(
        "waiting_for_content_value"
    ):

        return

    content_type = context.user_data.get(
        "new_content_type"
    )

    if content_type == "photo":

        await receive_photo_content(
            update,
            context,
        )

        return

    if content_type == "video":

        await receive_video_content(
            update,
            context,
        )

        return

    if content_type == "audio":

        await receive_audio_content(
            update,
            context,
        )

        return

    if content_type == "document":

        await receive_document_content(
            update,
            context,
        )

        return


# ==========================================
# أزرار Inline
# ==========================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await handle_content_callback(
        update,
        context,
    )


# ==========================================
# تأكيد الحذف
# ==========================================

async def handle_delete_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text

    if text == "✅ نعم، حذف":

        await confirm_delete_content(
            update,
            context,
        )

        return True

    return False


# ==========================================
# تشغيل البوت
# ==========================================

def main():

    initialize_database()

    # إضافة المشرف الأساسي تلقائيًا
    if ADMIN_ID:

        add_admin(
            ADMIN_ID
        )

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ======================================
    # الأوامر
    # ======================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin,
        )
    )

    # ======================================
    # أزرار Inline
    # ======================================

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # ======================================
    # الوسائط
    # ======================================

    application.add_handler(
        MessageHandler(
            filters.PHOTO
            | filters.VIDEO
            | filters.AUDIO
            | filters.Document.ALL,
            handle_media,
        )
    )

    # ======================================
    # النصوص
    # ======================================

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_text,
        )
    )

    print(
        "Huda People Bot is running..."
    )

    application.run_polling()


# ==========================================
# البداية
# ==========================================

if __name__ == "__main__":

    main()
