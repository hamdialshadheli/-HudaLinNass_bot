from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import (
    get_connection,
    next_display_order,
)

from bot.handlers.menus import show_menu


# ==========================================
# إزالة أيقونة المحتوى من اسم الزر
# ==========================================

def strip_content_icon(text):

    icons = [
        "📝 ",
        "🖼️ ",
        "🎥 ",
        "🎧 ",
        "📄 ",
        "🔗 ",
        "🖼️🎥🎧 ",
    ]

    for icon in icons:

        if text.startswith(icon):
            return text[len(icon):].strip()

    return text.strip()


# ==========================================
# أيقونة نوع المحتوى
# ==========================================

def content_icon(content_type):

    icons = {
        "text": "📝",
        "photo": "🖼️",
        "video": "🎥",
        "audio": "🎧",
        "document": "📄",
        "link": "🔗",
    }

    return icons.get(
        content_type,
        "📌",
    )


# ==========================================
# حفظ محتوى جديد
# ==========================================

async def save_content(
    context,
    menu_id,
    title,
    content_type,
    text_content=None,
    file_id=None,
    caption=None,
    description=None,
    url=None,
):

    display_order = next_display_order(
        menu_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO contents (
            menu_id,
            title,
            content_type,
            text_content,
            file_id,
            caption,
            description,
            url,
            sort_order,
            display_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            menu_id,
            title,
            content_type,
            text_content,
            file_id,
            caption,
            description,
            url,
            0,
            display_order,
        ),
    )

    content_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT OR IGNORE INTO content_stats (
            content_id,
            views
        )
        VALUES (?, 0)
        """,
        (content_id,),
    )

    connection.commit()
    connection.close()

    return content_id


# ==========================================
# بدء إضافة محتوى
# ==========================================

async def start_add_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not menu_id:

        await update.message.reply_text(
            "❌ افتح قائمة أولًا ثم اختر إضافة محتوى."
        )

        return

    context.user_data["adding_content"] = True

    from bot.keyboards import content_type_keyboard

    await update.message.reply_text(
        "📌 اختر نوع المحتوى:",
        reply_markup=content_type_keyboard(),
    )


# ==========================================
# اختيار نوع المحتوى
# ==========================================

async def select_content_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    content_type: str,
):

    context.user_data["new_content_type"] = (
        content_type
    )

    context.user_data["waiting_for_content_title"] = (
        True
    )

    from bot.keyboards import cancel_keyboard

    await update.message.reply_text(
        "✏️ اكتب عنوان المحتوى:",
        reply_markup=cancel_keyboard(),
    )


# ==========================================
# حفظ عنوان المحتوى
# ==========================================

async def receive_content_title(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    title = update.message.text.strip()

    if not title:

        await update.message.reply_text(
            "❌ العنوان لا يمكن أن يكون فارغًا."
        )

        return

    context.user_data[
        "new_content_title"
    ] = title

    context.user_data.pop(
        "waiting_for_content_title",
        None,
    )

    content_type = context.user_data.get(
        "new_content_type"
    )

    context.user_data[
        "waiting_for_content_value"
    ] = True

    from bot.keyboards import cancel_keyboard

    if content_type == "text":

        await update.message.reply_text(
            "📝 أرسل النص الآن.",
            reply_markup=cancel_keyboard(),
        )

    elif content_type == "link":

        await update.message.reply_text(
            "🔗 أرسل الرابط الآن.",
            reply_markup=cancel_keyboard(),
        )

    elif content_type == "photo":

        await update.message.reply_text(
            "🖼️ أرسل الصورة الآن.",
            reply_markup=cancel_keyboard(),
        )

    elif content_type == "video":

        await update.message.reply_text(
            "🎥 أرسل الفيديو الآن.",
            reply_markup=cancel_keyboard(),
        )

    elif content_type == "audio":

        await update.message.reply_text(
            "🎧 أرسل الصوت الآن.",
            reply_markup=cancel_keyboard(),
        )

    elif content_type == "document":

        await update.message.reply_text(
            "📄 أرسل الملف الآن.",
            reply_markup=cancel_keyboard(),
        )


# ==========================================
# حفظ النص
# ==========================================

async def receive_text_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    title = context.user_data.get(
        "new_content_title"
    )

    description = context.user_data.get(
        "new_content_description"
    )

    if not menu_id or not title:

        await update.message.reply_text(
            "❌ تعذر حفظ المحتوى."
        )

        return

    await save_content(
        context=context,
        menu_id=menu_id,
        title=title,
        content_type="text",
        text_content=update.message.text,
        description=description,
    )

    clear_new_content_state(context)

    await update.message.reply_text(
        "✅ تم حفظ النص بنجاح."
    )

    await show_menu(
        update,
        context,
        menu_id,
    )


# ==========================================
# حفظ الرابط
# ==========================================

async def receive_link_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    title = context.user_data.get(
        "new_content_title"
    )

    url = update.message.text.strip()

    if not url.startswith(
        ("http://", "https://")
    ):

        await update.message.reply_text(
            "❌ الرابط يجب أن يبدأ بـ:\n\n"
            "http://\n"
            "أو\n"
            "https://"
        )

        return

    await save_content(
        context=context,
        menu_id=menu_id,
        title=title,
        content_type="link",
        url=url,
    )

    clear_new_content_state(context)

    await update.message.reply_text(
        "✅ تم حفظ الرابط بنجاح."
    )

    await show_menu(
        update,
        context,
        menu_id,
    )


# ==========================================
# حفظ صورة
# ==========================================

async def receive_photo_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message.photo:
        return

    file_id = (
        update.message.photo[-1].file_id
    )

    await receive_media_content(
        update,
        context,
        "photo",
        file_id,
    )


# ==========================================
# حفظ فيديو
# ==========================================

async def receive_video_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message.video:
        return

    await receive_media_content(
        update,
        context,
        "video",
        update.message.video.file_id,
    )


# ==========================================
# حفظ صوت
# ==========================================

async def receive_audio_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message.audio:
        return

    await receive_media_content(
        update,
        context,
        "audio",
        update.message.audio.file_id,
    )


# ==========================================
# حفظ ملف
# ==========================================

async def receive_document_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message.document:
        return

    await receive_media_content(
        update,
        context,
        "document",
        update.message.document.file_id,
    )


# ==========================================
# حفظ الوسائط
# ==========================================

async def receive_media_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    content_type: str,
    file_id: str,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    title = context.user_data.get(
        "new_content_title"
    )

    description = context.user_data.get(
        "new_content_description"
    )

    caption = update.message.caption

    await save_content(
        context=context,
        menu_id=menu_id,
        title=title,
        content_type=content_type,
        file_id=file_id,
        caption=caption,
        description=description,
    )

    clear_new_content_state(context)

    await update.message.reply_text(
        "✅ تم حفظ المحتوى بنجاح."
    )

    await show_menu(
        update,
        context,
        menu_id,
    )


# ==========================================
# تنظيف حالة إضافة المحتوى
# ==========================================

def clear_new_content_state(context):

    keys = [
        "adding_content",
        "new_content_type",
        "new_content_title",
        "new_content_description",
        "waiting_for_content_title",
        "waiting_for_content_value",
    ]

    for key in keys:
        context.user_data.pop(
            key,
            None,
        )


# ==========================================
# عرض المحتوى للمستخدم
# ==========================================

async def send_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    content,
):

    content_id = content["id"]

    connection = get_connection()

    connection.execute(
        """
        INSERT OR IGNORE INTO content_stats (
            content_id,
            views
        )
        VALUES (?, 0)
        """,
        (content_id,),
    )

    connection.execute(
        """
        UPDATE content_stats
        SET views = views + 1
        WHERE content_id = ?
        """,
        (content_id,),
    )

    connection.commit()
    connection.close()

    # الوصف
    if content["description"]:

        await update.message.reply_text(
            content["description"]
        )

    content_type = content[
        "content_type"
    ]

    # النص
    if content_type == "text":

        await update.message.reply_text(
            content["text_content"] or ""
        )

    # الصورة
    elif content_type == "photo":

        await update.message.reply_photo(
            content["file_id"],
            caption=content["caption"] or None,
        )

    # الفيديو
    elif content_type == "video":

        await update.message.reply_video(
            content["file_id"],
            caption=content["caption"] or None,
        )

    # الصوت
    elif content_type == "audio":

        await update.message.reply_audio(
            content["file_id"],
            caption=content["caption"] or None,
        )

    # الملف
    elif content_type == "document":

        await update.message.reply_document(
            content["file_id"],
            caption=content["caption"] or None,
        )

    # الرابط
    elif content_type == "link":

        await update.message.reply_text(
            content["url"] or ""
        )


# ==========================================
# البحث عن المحتوى داخل القائمة الحالية
# ==========================================

async def open_content_by_title(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not menu_id:
        return False

    connection = get_connection()

    content = connection.execute(
        """
        SELECT *
        FROM contents
        WHERE menu_id = ?
        AND title = ?
        LIMIT 1
        """,
        (
            menu_id,
            title,
        ),
    ).fetchone()

    connection.close()

    if not content:
        return False

    await send_content(
        update,
        context,
        content,
    )

    return True


# ==========================================
# عرض قائمة تعديل المحتوى
# ==========================================

async def list_editable_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not menu_id:

        await update.message.reply_text(
            "❌ افتح قائمة أولًا."
        )

        return

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            title,
            content_type
        FROM contents
        WHERE menu_id = ?
        ORDER BY display_order, id
        """,
        (menu_id,),
    ).fetchall()

    connection.close()

    if not rows:

        await update.message.reply_text(
            "ℹ️ لا يوجد محتوى داخل هذه القائمة."
        )

        return

    buttons = []

    for row in rows:

        icon = content_icon(
            row["content_type"]
        )

        buttons.append([
            InlineKeyboardButton(
                f"{icon} {row['title']}",
                callback_data=f"edit_content:{row['id']}",
            )
        ])

    await update.message.reply_text(
        "✏️ اختر المحتوى الذي تريد تعديله:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# ==========================================
# عرض قائمة حذف المحتوى
# ==========================================

async def list_deletable_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not menu_id:

        await update.message.reply_text(
            "❌ افتح قائمة أولًا."
        )

        return

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            title,
            content_type
        FROM contents
        WHERE menu_id = ?
        ORDER BY display_order, id
        """,
        (menu_id,),
    ).fetchall()

    connection.close()

    if not rows:

        await update.message.reply_text(
            "ℹ️ لا يوجد محتوى لحذفه."
        )

        return

    buttons = []

    for row in rows:

        icon = content_icon(
            row["content_type"]
        )

        buttons.append([
            InlineKeyboardButton(
                f"{icon} {row['title']}",
                callback_data=f"delete_content:{row['id']}",
            )
        ])

    await update.message.reply_text(
        "🗑️ اختر المحتوى الذي تريد حذفه:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# ==========================================
# معالجة أزرار التعديل والحذف
# ==========================================

async def handle_content_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # ======================================
    # تعديل المحتوى
    # ======================================

    if data.startswith(
        "edit_content:"
    ):

        content_id = int(
            data.split(":")[1]
        )

        context.user_data[
            "editing_content_id"
        ] = content_id

        await query.edit_message_text(
            "✏️ اختر الحقل الذي تريد تعديله:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "العنوان",
                        callback_data="edit_field:title",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "الوصف",
                        callback_data="edit_field:description",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "النص",
                        callback_data="edit_field:text_content",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "الرابط",
                        callback_data="edit_field:url",
                    )
                ],
            ]),
        )

        return

    # ======================================
    # تحديد حقل التعديل
    # ======================================

    if data.startswith(
        "edit_field:"
    ):

        field = data.split(":")[1]

        content_id = context.user_data.get(
            "editing_content_id"
        )

        if not content_id:
            return

        context.user_data[
            "editing_field"
        ] = field

        context.user_data[
            "waiting_for_edit_value"
        ] = True

        await query.message.reply_text(
            "✏️ أرسل القيمة الجديدة الآن."
        )

        return

    # ======================================
    # حذف المحتوى
    # ======================================

    if data.startswith(
        "delete_content:"
    ):

        content_id = int(
            data.split(":")[1]
        )

        connection = get_connection()

        content = connection.execute(
            """
            SELECT
                id,
                title
            FROM contents
            WHERE id = ?
            """,
            (content_id,),
        ).fetchone()

        connection.close()

        if not content:

            await query.edit_message_text(
                "❌ المحتوى غير موجود."
            )

            return

        context.user_data[
            "delete_content_id"
        ] = content_id

        await query.edit_message_text(
            f"⚠️ هل تريد حذف:\n\n"
            f"«{content['title']}»"
        )

        from bot.keyboards import confirm_delete_keyboard

        await query.message.reply_text(
            "تأكيد الحذف:",
            reply_markup=confirm_delete_keyboard(),
        )

        return


# ==========================================
# تنفيذ تعديل المحتوى
# ==========================================

async def save_edit_value(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    content_id = context.user_data.get(
        "editing_content_id"
    )

    field = context.user_data.get(
        "editing_field"
    )

    if not content_id or not field:
        return False

    value = update.message.text

    allowed_fields = {
        "title": "title",
        "description": "description",
        "text_content": "text_content",
        "url": "url",
    }

    column = allowed_fields.get(
        field
    )

    if not column:
        return False

    if field == "url" and not value.startswith(
        ("http://", "https://")
    ):

        await update.message.reply_text(
            "❌ الرابط يجب أن يبدأ بـ http:// أو https://"
        )

        return True

    connection = get_connection()

    connection.execute(
        f"""
        UPDATE contents
        SET {column} = ?
        WHERE id = ?
        """,
        (
            value,
            content_id,
        ),
    )

    connection.commit()

    content = connection.execute(
        """
        SELECT menu_id
        FROM contents
        WHERE id = ?
        """,
        (content_id,),
    ).fetchone()

    connection.close()

    context.user_data.pop(
        "editing_content_id",
        None,
    )

    context.user_data.pop(
        "editing_field",
        None,
    )

    context.user_data.pop(
        "waiting_for_edit_value",
        None,
    )

    await update.message.reply_text(
        "✅ تم تعديل المحتوى بنجاح."
    )

    if content:

        await show_menu(
            update,
            context,
            content["menu_id"],
        )

    return True


# ==========================================
# تأكيد حذف المحتوى
# ==========================================

async def confirm_delete_content(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    content_id = context.user_data.pop(
        "delete_content_id",
        None,
    )

    if not content_id:

        await update.message.reply_text(
            "❌ لا توجد عملية حذف معلقة."
        )

        return

    connection = get_connection()

    content = connection.execute(
        """
        SELECT
            menu_id,
            title
        FROM contents
        WHERE id = ?
        """,
        (content_id,),
    ).fetchone()

    if not content:

        connection.close()

        await update.message.reply_text(
            "❌ المحتوى غير موجود."
        )

        return

    connection.execute(
        """
        DELETE FROM content_stats
        WHERE content_id = ?
        """,
        (content_id,),
    )

    connection.execute(
        """
        DELETE FROM contents
        WHERE id = ?
        """,
        (content_id,),
    )

    connection.commit()

    connection.close()

    await update.message.reply_text(
        f"🗑️ تم حذف «{content['title']}» بنجاح."
    )

    await show_menu(
        update,
        context,
        content["menu_id"],
    )
