from telegram import Update
from telegram.ext import ContextTypes

from bot.database import (
    get_connection,
    next_display_order,
)

from bot.handlers.menus import show_menu


# ==========================================
# بدء إنشاء مجموعة وسائط
# ==========================================

async def start_media_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not menu_id:
        await update.message.reply_text(
            "❌ افتح قائمة أولًا ثم أنشئ مجموعة الوسائط."
        )
        return

    context.user_data["creating_media_group"] = True

    await update.message.reply_text(
        "🖼️🎥🎧 اكتب اسم مجموعة الوسائط:"
    )


# ==========================================
# استقبال اسم المجموعة
# ==========================================

async def receive_group_title(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    title = (
        update.message.text
        or ""
    ).strip()

    if not title:
        await update.message.reply_text(
            "❌ اسم المجموعة لا يمكن أن يكون فارغًا."
        )
        return

    context.user_data[
        "new_group_title"
    ] = title

    context.user_data.pop(
        "creating_media_group",
        None,
    )

    context.user_data[
        "waiting_for_group_description"
    ] = True

    await update.message.reply_text(
        "📝 اكتب وصف المجموعة، أو اكتب:\n\n"
        "بدون وصف"
    )


# ==========================================
# استقبال وصف المجموعة
# ==========================================

async def receive_group_description(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    description = (
        update.message.text
        or ""
    ).strip()

    if description == "بدون وصف":
        description = None

    context.user_data[
        "new_group_description"
    ] = description

    context.user_data.pop(
        "waiting_for_group_description",
        None,
    )

    context.user_data[
        "waiting_for_group_media"
    ] = True

    await update.message.reply_text(
        "📥 أرسل الآن الوسائط واحدًا تلو الآخر.\n\n"
        "يمكنك إرسال صور أو فيديوهات أو ملفات صوتية.\n\n"
        "بعد الانتهاء اضغط:\n"
        "✅ إنهاء المجموعة"
    )


# ==========================================
# حفظ عنصر داخل المجموعة
# ==========================================

async def save_group_item(
    context,
    file_id,
    caption=None,
):

    group_id = context.user_data.get(
        "new_group_id"
    )

    if not group_id:
        return

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            COALESCE(
                MAX(sort_order),
                -1
            ) + 1 AS next_order
        FROM media_group_items
        WHERE group_id = ?
        """,
        (group_id,),
    )

    sort_order = cursor.fetchone()[
        "next_order"
    ]

    cursor.execute(
        """
        INSERT INTO media_group_items (
            group_id,
            file_id,
            caption,
            sort_order
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            group_id,
            file_id,
            caption,
            sort_order,
        ),
    )

    connection.commit()
    connection.close()


# ==========================================
# إنشاء سجل المجموعة عند أول وسائط
# ==========================================

async def ensure_group_created(
    context,
    media_type,
):

    existing_group_id = context.user_data.get(
        "new_group_id"
    )

    if existing_group_id:
        return existing_group_id

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    title = context.user_data.get(
        "new_group_title"
    )

    description = context.user_data.get(
        "new_group_description"
    )

    if not menu_id or not title:
        return None

    display_order = next_display_order(
        menu_id
    )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO media_groups (
            menu_id,
            title,
            description,
            media_type,
            sort_order,
            display_order
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            menu_id,
            title,
            description,
            media_type,
            0,
            display_order,
        ),
    )

    group_id = cursor.lastrowid

    connection.commit()
    connection.close()

    context.user_data[
        "new_group_id"
    ] = group_id

    return group_id


# ==========================================
# استقبال صورة
# ==========================================

async def receive_group_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get(
        "waiting_for_group_media"
    ):
        return

    if not update.message.photo:
        return

    group_id = await ensure_group_created(
        context,
        "mixed",
    )

    if not group_id:
        return

    file_id = update.message.photo[-1].file_id

    await save_group_item(
        context,
        file_id,
        update.message.caption,
    )

    await update.message.reply_text(
        "✅ تمت إضافة الصورة إلى المجموعة."
    )


# ==========================================
# استقبال فيديو
# ==========================================

async def receive_group_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get(
        "waiting_for_group_media"
    ):
        return

    if not update.message.video:
        return

    group_id = await ensure_group_created(
        context,
        "mixed",
    )

    if not group_id:
        return

    await save_group_item(
        context,
        update.message.video.file_id,
        update.message.caption,
    )

    await update.message.reply_text(
        "✅ تمت إضافة الفيديو إلى المجموعة."
    )


# ==========================================
# استقبال صوت
# ==========================================

async def receive_group_audio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get(
        "waiting_for_group_media"
    ):
        return

    if not update.message.audio:
        return

    group_id = await ensure_group_created(
        context,
        "mixed",
    )

    if not group_id:
        return

    await save_group_item(
        context,
        update.message.audio.file_id,
        update.message.caption,
    )

    await update.message.reply_text(
        "✅ تمت إضافة الملف الصوتي إلى المجموعة."
    )


# ==========================================
# إنهاء المجموعة
# ==========================================

async def finish_media_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    group_id = context.user_data.get(
        "new_group_id"
    )

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not group_id:

        await update.message.reply_text(
            "❌ لم تتم إضافة أي وسائط إلى المجموعة."
        )

        clear_group_state(context)

        return

    connection = get_connection()

    count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM media_group_items
        WHERE group_id = ?
        """,
        (group_id,),
    ).fetchone()["count"]

    connection.close()

    if count == 0:

        await update.message.reply_text(
            "❌ المجموعة فارغة."
        )

        return

    clear_group_state(context)

    await update.message.reply_text(
        f"✅ تم إنشاء مجموعة الوسائط بنجاح.\n\n"
        f"📦 عدد العناصر: {count}"
    )

    if menu_id:
        await show_menu(
            update,
            context,
            menu_id,
        )


# ==========================================
# مسح حالات المجموعة
# ==========================================

def clear_group_state(context):

    keys = [
        "creating_media_group",
        "new_group_title",
        "new_group_description",
        "new_group_id",
        "waiting_for_group_description",
        "waiting_for_group_media",
    ]

    for key in keys:
        context.user_data.pop(
            key,
            None,
        )


# ==========================================
# فتح مجموعة وسائط
# ==========================================

async def open_media_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    title,
):

    menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not menu_id:
        return False

    connection = get_connection()

    group = connection.execute(
        """
        SELECT *
        FROM media_groups
        WHERE menu_id = ?
        AND title = ?
        LIMIT 1
        """,
        (
            menu_id,
            title,
        ),
    ).fetchone()

    if not group:
        connection.close()
        return False

    items = connection.execute(
        """
        SELECT *
        FROM media_group_items
        WHERE group_id = ?
        ORDER BY sort_order, id
        """,
        (group["id"],),
    ).fetchall()

    connection.close()

    if group["description"]:

        await update.message.reply_text(
            group["description"]
        )

    if not items:

        await update.message.reply_text(
            "ℹ️ هذه المجموعة لا تحتوي على وسائط."
        )

        return True

    for item in items:

        await update.message.reply_document(
            item["file_id"],
            caption=item["caption"] or None,
        )

    return True
