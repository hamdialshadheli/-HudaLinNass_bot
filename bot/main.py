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
    user_keyboard,
    admin_keyboard,
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
    start_add_admin,
    receive_admin_id,
    start_remove_admin,
    receive_remove_admin_id,
)

from bot.handlers.media_groups import (
    start_media_group,
    receive_group_title,
    receive_group_description,
    receive_group_photo,
    receive_group_video,
    receive_group_audio,
    finish_media_group,
)


load_dotenv()

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
).strip()

ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "0",
    )
)


# ==================================================
# واجهة المستخدم العامة
# ==================================================

async def show_public_home(
    update,
    context,
):
    is_admin_user = is_admin(
        update.effective_user.id
    )

    keyboard = user_keyboard(
        is_admin_user=is_admin_user
    )

    # اختبار: معرفة الواجهة التي ينشئها البوت فعليًا
    print(
        "PUBLIC KEYBOARD:",
        keyboard.keyboard,
        flush=True,
    )

    await update.message.reply_text(
        "🌿 مرحباً بك في هدى للناس",
        reply_markup=keyboard,
    )


# ==================================================
# START
# ==================================================

async def start(
    update,
    context,
):
    register_user(
        update.effective_user
    )

    context.user_data.clear()

    await show_public_home(
        update,
        context,
    )


# ==================================================
# ADMIN
# ==================================================

async def admin(
    update,
    context,
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

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ لوحة تحكم هدى للناس",
        reply_markup=admin_keyboard(),
    )


# ==================================================
# فتح واجهة المستخدم من الأدمن
# ==================================================

async def show_user_interface(
    update,
    context,
):
    context.user_data.clear()

    await show_public_home(
        update,
        context,
    )


# ==================================================
# فتح قائمة أو فرع
# ==================================================

async def open_menu_from_button(
    update,
    context,
    text,
):
    menu_name = text[
        len("📂 "):
    ].strip()

    current_menu_id = context.user_data.get(
        "current_menu_id"
    )

    connection = get_connection()

    menu = None

    if current_menu_id:
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

    if not menu:
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
        await update.message.reply_text(
            "❌ القائمة أو الفرع غير موجود."
        )
        return

    await show_menu(
        update,
        context,
        menu["id"],
    )


# ==================================================
# إدارة القوائم
# ==================================================

async def manage_menus(
    update,
    context,
):
    connection = get_connection()

    roots = connection.execute(
        """
        SELECT
            id,
            name
        FROM menus
        WHERE parent_id IS NULL
        ORDER BY
            CASE
                WHEN display_order IS NULL THEN 1
                ELSE 0
            END,
            display_order,
            id
        """
    ).fetchall()

    connection.close()

    keyboard = []

    for root in roots:
        keyboard.append(
            [f"📂 {root['name']}"]
        )

    keyboard.append(
        ["◀️ رجوع"]
    )

    context.user_data.pop(
        "current_menu_id",
        None,
    )

    context.user_data.pop(
        "current_menu_name",
        None,
    )

    if not roots:
        await update.message.reply_text(
            "ℹ️ لا توجد قوائم حاليًا.",
            reply_markup=admin_keyboard(),
        )
        return

    await update.message.reply_text(
        "📂 إدارة القوائم\n\nاختر القائمة التي تريد إدارتها:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


# ==================================================
# إلغاء
# ==================================================

async def handle_cancel(
    update,
    context,
):
    context.user_data.clear()

    if is_admin(
        update.effective_user.id
    ):
        await update.message.reply_text(
            "❌ تم إلغاء العملية.",
            reply_markup=admin_keyboard(),
        )
    else:
        await show_public_home(
            update,
            context,
        )


# ==================================================
# TEXT ROUTER
# ==================================================

async def handle_text(
    update,
    context,
):
    register_user(
        update.effective_user
    )

    text = (
        update.message.text or ""
    ).strip()

    user_id = update.effective_user.id

    # ----------------------------------------------
    # إلغاء
    # ----------------------------------------------

    if text == "❌ إلغاء":
        await handle_cancel(
            update,
            context,
        )
        return

    # ----------------------------------------------
    # رجوع
    # ----------------------------------------------

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

        context.user_data.pop(
            "waiting_for_admin_id",
            None,
        )

        context.user_data.pop(
            "waiting_for_remove_admin_id",
            None,
        )

        context.user_data.pop(
            "waiting_for_group_description",
            None,
        )

        context.user_data.pop(
            "waiting_for_group_media",
            None,
        )

        context.user_data.pop(
            "creating_media_group",
            None,
        )

        await go_back_one_level(
            update,
            context,
        )

        return

    # ----------------------------------------------
    # واجهة المستخدم
    # ----------------------------------------------

    if text == "👤 واجهة المستخدم":

        if not is_admin(user_id):
            await update.message.reply_text(
                "⛔ ليس لديك صلاحية."
            )
            return

        await show_user_interface(
            update,
            context,
        )

        return

    # ----------------------------------------------
    # الإدارة
    # ----------------------------------------------

    if text == "⚙️ الإدارة":

        await admin(
            update,
            context,
        )

        return

    # ----------------------------------------------
    # المستخدم: الأقسام الرئيسية
    # ----------------------------------------------

    if text in (
        "📖 القرآن والثقافة",
        "📚 الملازم",
        "🎧 المحاضرات",
    ):

        menu_name = text[2:].strip()

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

        if menu:

            context.user_data["menu_path"] = []

            await show_menu(
                update,
                context,
                menu["id"],
            )

        else:

            await update.message.reply_text(
                f"ℹ️ قسم {menu_name} غير متاح حاليًا."
            )

        return

    # ----------------------------------------------
    # عن البوت
    # ----------------------------------------------

    if text == "ℹ️ عن البوت":

        await update.message.reply_text(
            "🌿 هدى للناس\n\n"
            "منصة ثقافية ومعرفية لخدمة المستخدمين "
            "وتسهيل الوصول إلى المحتوى."
        )

        return

    # =================================================
    # المشرف
    # =================================================

    if is_admin(user_id):

        # ---------------------------------------------
        # إنشاء قائمة رئيسية
        # ---------------------------------------------

        if text in (
            "➕ إنشاء قائمة",
            "➕ إضافة قائمة",
        ):

            context.user_data[
                "waiting_for_root_name"
            ] = True

            await update.message.reply_text(
                "📂 اكتب اسم القائمة الرئيسية:",
                reply_markup=cancel_keyboard(),
            )

            return

        # ---------------------------------------------
        # إدارة القوائم
        # ---------------------------------------------

        if text == "📂 إدارة القوائم":

            await manage_menus(
                update,
                context,
            )

            return

        # ---------------------------------------------
        # إضافة فرع
        # ---------------------------------------------

        if text == "➕ إضافة فرع":

            current_menu_id = context.user_data.get(
                "current_menu_id"
            )

            if not current_menu_id:

                await update.message.reply_text(
                    "❌ افتح القائمة التي تريد إضافة الفرع "
                    "بداخلها أولًا."
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

        # ---------------------------------------------
        # إضافة محتوى
        # ---------------------------------------------

        if text == "➕ إضافة محتوى":

            await start_add_content(
                update,
                context,
            )

            return

        # ---------------------------------------------
        # أنواع المحتوى
        # ---------------------------------------------

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

        # ---------------------------------------------
        # مجموعة الوسائط
        # ---------------------------------------------

        if text == "🖼️🎥🎧 مجموعة وسائط":

            await start_media_group(
                update,
                context,
            )

            return

        if text == "✅ إنهاء المجموعة":

            await finish_media_group(
                update,
                context,
            )

            return

        # ---------------------------------------------
        # تعديل المحتوى
        # ---------------------------------------------

        if text == "✏️ تعديل المحتوى":

            await list_editable_content(
                update,
                context,
            )

            return

        # ---------------------------------------------
        # حذف المحتوى
        # ---------------------------------------------

        if text == "🗑️ حذف المحتوى":

            await list_deletable_content(
                update,
                context,
            )

            return

        # ---------------------------------------------
        # ترتيب
        # ---------------------------------------------

        if text == "↕️ ترتيب العناصر":

            await update.message.reply_text(
                "↕️ ترتيب العناصر سيتم تفعيله "
                "في المرحلة التالية."
            )

            return

        # ---------------------------------------------
        # المشرفون
        # ---------------------------------------------

        if text == "👥 إدارة المشرفين":

            await show_admins(
                update,
                context,
            )

            return

        # دعم الاسم القديم
        if text == "👥 المشرفون":

            await show_admins(
                update,
                context,
            )

            return

        if text == "➕ إضافة مشرف":

            await start_add_admin(
                update,
                context,
            )

            return

        if text == "🗑️ حذف مشرف":

            await start_remove_admin(
                update,
                context,
            )

            return

        # ---------------------------------------------
        # الإحصائيات
        # ---------------------------------------------

        if text == "📊 الإحصائيات":

            await show_stats(
                update,
                context,
            )

            return

        # =================================================
        # الحالات التي تنتظر إدخال المستخدم
        # =================================================

        # اسم القائمة الرئيسية
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

        # اسم الفرع
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

        # عنوان المحتوى
        if context.user_data.get(
            "waiting_for_content_title"
        ):

            await receive_content_title(
                update,
                context,
            )

            return

        # محتوى نص أو رابط
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

        # اسم مجموعة الوسائط
        if context.user_data.get(
            "creating_media_group"
        ):

            await receive_group_title(
                update,
                context,
            )

            return

        # وصف المجموعة
        if context.user_data.get(
            "waiting_for_group_description"
        ):

            await receive_group_description(
                update,
                context,
            )

            return

        # إضافة مشرف
        if context.user_data.get(
            "waiting_for_admin_id"
        ):

            await receive_admin_id(
                update,
                context,
            )

            return

        # حذف مشرف
        if context.user_data.get(
            "waiting_for_remove_admin_id"
        ):

            await receive_remove_admin_id(
                update,
                context,
            )

            return

        # تعديل المحتوى
        if context.user_data.get(
            "waiting_for_edit_value"
        ):

            await save_edit_value(
                update,
                context,
            )

            return

        # تأكيد الحذف
        if text == "✅ نعم، حذف":

            await confirm_delete_content(
                update,
                context,
            )

            return

    # ==================================================
    # فتح قائمة أو فرع
    # ==================================================

    if text.startswith("📂 "):

        await open_menu_from_button(
            update,
            context,
            text,
        )

        return

    # ==================================================
    # فتح المحتوى
    # ==================================================

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


# ==================================================
# MEDIA ROUTER
# ==================================================

async def handle_media(
    update,
    context,
):
    # مجموعة الوسائط
    if context.user_data.get(
        "waiting_for_group_media"
    ):

        if update.message.photo:

            await receive_group_photo(
                update,
                context,
            )

            return

        if update.message.video:

            await receive_group_video(
                update,
                context,
            )

            return

        if update.message.audio:

            await receive_group_audio(
                update,
                context,
            )

            return

    # محتوى منفرد
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


# ==================================================
# CALLBACKS
# ==================================================

async def callback_handler(
    update,
    context,
):
    if not is_admin(
        update.effective_user.id
    ):

        await update.callback_query.answer(
            "⛔ ليس لديك صلاحية.",
            show_alert=True,
        )

        return

    await handle_content_callback(
        update,
        context,
    )


# ==================================================
# MAIN
# ==================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN غير موجود."
        )

    initialize_database()

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

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO
            | filters.VIDEO
            | filters.AUDIO
            | filters.Document.ALL,
            handle_media,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_text,
        )
    )

    print(
        "Huda People Bot is running...",
        flush=True,
    )

    application.run_polling()


if __name__ == "__main__":
    main()
