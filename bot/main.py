import os

from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from database import (
    initialize_database,
    get_connection,
)


# =========================================================
# الإعدادات
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")


# =========================================================
# تهيئة قاعدة البيانات
# =========================================================

initialize_database()


# =========================================================
# لوحة المستخدم الرئيسية
# =========================================================

MAIN_KEYBOARD = [
    ["📖 القرآن والثقافة"],
    ["📚 الملازم"],
    ["🎧 المحاضرات"],
    ["ℹ️ عن البوت"],
]


# =========================================================
# لوحة المشرف
# =========================================================

def admin_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["➕ إضافة قائمة"],
            ["📋 إدارة القوائم"],
        ],
        resize_keyboard=True
    )


# =========================================================
# لوحة إدارة القائمة
# =========================================================

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
        (menu_id,)
    )

    menus = cursor.fetchall()

    # المحتويات
    cursor.execute(
        """
        SELECT id, title, content_type
        FROM contents
        WHERE menu_id = ?
        ORDER BY sort_order, id
        """,
        (menu_id,)
    )

    contents = cursor.fetchall()

    connection.close()

    keyboard = []

    # -----------------------------
    # الفروع
    # -----------------------------

    for menu in menus:
        keyboard.append(
            [f"📂 {menu['name']}"]
        )

    # -----------------------------
    # المحتويات
    # -----------------------------

    icons = {
        "text": "📝",
        "photo": "🖼️",
        "video": "🎬",
        "audio": "🎵",
    }

    for content in contents:

        icon = icons.get(
            content["content_type"],
            "📄"
        )

        keyboard.append(
            [f"{icon} {content['title']}"]
        )

    # -----------------------------
    # الإدارة
    # -----------------------------

    keyboard.extend(
        [
            ["➕ إضافة فرع"],
            ["📝 إضافة نص"],
            ["🖼️ إضافة صورة"],
            ["🎬 إضافة فيديو"],
            ["🎵 إضافة صوت"],
            ["◀️ رجوع"],
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


# =========================================================
# عرض القائمة
# =========================================================

async def show_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    menu_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, name, parent_id
        FROM menus
        WHERE id = ?
        """,
        (menu_id,)
    )

    menu = cursor.fetchone()

    connection.close()

    if not menu:
        await update.message.reply_text(
            "❌ القائمة غير موجودة."
        )
        return

    context.user_data["current_menu_id"] = menu["id"]
    context.user_data["current_menu_name"] = menu["name"]

    await update.message.reply_text(
        f"📂 {menu['name']}",
        reply_markup=menu_keyboard(menu["id"])
    )


# =========================================================
# /start
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "🌿 أهلاً بك في بوت هدى للناس",
        reply_markup=ReplyKeyboardMarkup(
            MAIN_KEYBOARD,
            resize_keyboard=True
        )
    )


# =========================================================
# /admin
# =========================================================

async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = str(update.effective_user.id)

    if user_id != str(ADMIN_ID):

        await update.message.reply_text(
            "❌ ليس لديك صلاحية الدخول إلى لوحة الإدارة."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ لوحة إدارة البوت",
        reply_markup=admin_keyboard()
    )


# =========================================================
# حفظ المحتوى
# =========================================================

def save_content(
    menu_id,
    title,
    content_type,
    text_content=None,
    file_id=None,
    caption=None,
    description=None
):

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
            description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            menu_id,
            title,
            content_type,
            text_content,
            file_id,
            caption,
            description
        )
    )

    connection.commit()
    connection.close()


# =========================================================
# البحث عن القائمة
# =========================================================

def find_menu(menu_name):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM menus
        WHERE name = ?
        LIMIT 1
        """,
        (menu_name,)
    )

    menu = cursor.fetchone()

    connection.close()

    return menu


# =========================================================
# البحث عن المحتوى
# =========================================================

def find_content(title):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM contents
        WHERE title = ?
        LIMIT 1
        """,
        (title,)
    )

    content = cursor.fetchone()

    connection.close()

    return content


# =========================================================
# إرسال المحتوى
# =========================================================

async def send_content(
    update: Update,
    content
):

    description = content["description"]

    # -----------------------------------------
    # النص
    # -----------------------------------------

    if content["content_type"] == "text":

        text = content["text_content"] or ""

        if description:
            text = (
                f"📝 {content['title']}\n\n"
                f"{description}\n\n"
                f"{text}"
            )

        await update.message.reply_text(
            text
        )

    # -----------------------------------------
    # الصورة
    # -----------------------------------------

    elif content["content_type"] == "photo":

        caption = f"🖼️ {content['title']}"

        if description:
            caption += f"\n\n📝 {description}"

        await update.message.reply_photo(
            photo=content["file_id"],
            caption=caption
        )

    # -----------------------------------------
    # الفيديو
    # -----------------------------------------

    elif content["content_type"] == "video":

        caption = f"🎬 {content['title']}"

        if description:
            caption += f"\n\n📝 {description}"

        await update.message.reply_video(
            video=content["file_id"],
            caption=caption
        )

    # -----------------------------------------
    # الصوت
    # -----------------------------------------

    elif content["content_type"] == "audio":

        caption = f"🎵 {content['title']}"

        if description:
            caption += f"\n\n📝 {description}"

        await update.message.reply_audio(
            audio=content["file_id"],
            caption=caption
        )


# =========================================================
# معالجة الرسائل
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    user_id = str(update.effective_user.id)

    is_admin = (
        user_id == str(ADMIN_ID)
    )

    # =====================================================
    # زر الرجوع
    # =====================================================

    if text == "◀️ رجوع":

        # إلغاء أي عملية إضافة
        context.user_data.pop(
            "waiting_for_menu_name",
            None
        )

        context.user_data.pop(
            "waiting_for_branch_name",
            None
        )

        context.user_data.pop(
            "waiting_for_text_title",
            None
        )

        context.user_data.pop(
            "waiting_for_text_content",
            None
        )

        context.user_data.pop(
            "waiting_for_photo_title",
            None
        )

        context.user_data.pop(
            "waiting_for_photo_description",
            None
        )

        context.user_data.pop(
            "waiting_for_video_title",
            None
        )

        context.user_data.pop(
            "waiting_for_video_description",
            None
        )

        context.user_data.pop(
            "waiting_for_audio_title",
            None
        )

        context.user_data.pop(
            "waiting_for_audio_description",
            None
        )

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        if current_menu_id:

            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT parent_id
                FROM menus
                WHERE id = ?
                """,
                (current_menu_id,)
            )

            menu = cursor.fetchone()

            connection.close()

            if menu and menu["parent_id"]:

                await show_menu(
                    update,
                    context,
                    menu["parent_id"]
                )

            else:

                context.user_data.clear()

                await update.message.reply_text(
                    "⚙️ لوحة إدارة البوت",
                    reply_markup=admin_keyboard()
                )

        else:

            await update.message.reply_text(
                "⚙️ لوحة إدارة البوت",
                reply_markup=admin_keyboard()
            )

        return

    # =====================================================
    # إضافة قائمة رئيسية
    # =====================================================

    if is_admin and text == "➕ إضافة قائمة":

        context.user_data[
            "waiting_for_menu_name"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل اسم القائمة الجديدة:"
        )

        return

    # =====================================================
    # حفظ القائمة الرئيسية
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_menu_name"
    ):

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO menus (
                name,
                parent_id
            )
            VALUES (?, NULL)
            """,
            (text,)
        )

        connection.commit()
        connection.close()

        context.user_data.pop(
            "waiting_for_menu_name"
        )

        await update.message.reply_text(
            f"✅ تم إنشاء القائمة:\n\n📂 {text}",
            reply_markup=admin_keyboard()
        )

        return

    # =====================================================
    # إدارة القوائم
    # =====================================================

    if is_admin and text == "📋 إدارة القوائم":

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

        keyboard = []

        for menu in menus:

            keyboard.append(
                [f"📂 {menu['name']}"]
            )

        keyboard.append(
            ["◀️ رجوع"]
        )

        await update.message.reply_text(
            "📋 اختر القائمة التي تريد إدارتها:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )
        )

        return

    # =====================================================
    # إضافة فرع
    # =====================================================

    if is_admin and text == "➕ إضافة فرع":

        if not context.user_data.get(
            "current_menu_id"
        ):

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "waiting_for_branch_name"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل اسم الفرع:"
        )

        return

    # =====================================================
    # حفظ الفرع
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_branch_name"
    ):

        parent_id = context.user_data.get(
            "current_menu_id"
        )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO menus (
                name,
                parent_id
            )
            VALUES (?, ?)
            """,
            (
                text,
                parent_id
            )
        )

        connection.commit()
        connection.close()

        context.user_data.pop(
            "waiting_for_branch_name"
        )

        await update.message.reply_text(
            f"✅ تم إنشاء الفرع:\n\n📂 {text}",
            reply_markup=menu_keyboard(
                parent_id
            )
        )

        return

    # =====================================================
    # إضافة نص
    # =====================================================

    if is_admin and text == "📝 إضافة نص":

        if not context.user_data.get(
            "current_menu_id"
        ):

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "waiting_for_text_title"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل عنوان النص:"
        )

        return

    # =====================================================
    # عنوان النص
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_text_title"
    ):

        context.user_data[
            "new_text_title"
        ] = text

        context.user_data.pop(
            "waiting_for_text_title"
        )

        context.user_data[
            "waiting_for_text_content"
        ] = True

        await update.message.reply_text(
            "📝 أرسل محتوى النص:"
        )

        return

    # =====================================================
    # محتوى النص
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_text_content"
    ):

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "new_text_title"
        )

        save_content(
            menu_id=menu_id,
            title=title,
            content_type="text",
            text_content=text
        )

        context.user_data.pop(
            "waiting_for_text_content"
        )

        context.user_data.pop(
            "new_text_title",
            None
        )

        await update.message.reply_text(
            "✅ تم حفظ النص.",
            reply_markup=menu_keyboard(
                menu_id
            )
        )

        return

    # =====================================================
    # إضافة صورة
    # =====================================================

    if is_admin and text == "🖼️ إضافة صورة":

        if not context.user_data.get(
            "current_menu_id"
        ):

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "waiting_for_photo_title"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل عنوان الصورة:"
        )

        return

    # =====================================================
    # عنوان الصورة
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_photo_title"
    ):

        context.user_data[
            "new_photo_title"
        ] = text

        context.user_data.pop(
            "waiting_for_photo_title"
        )

        context.user_data[
            "waiting_for_photo_description"
        ] = True

        await update.message.reply_text(
            "📝 أرسل شرح الصورة أو اكتب:\n\nبدون شرح"
        )

        return

    # =====================================================
    # وصف الصورة
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_photo_description"
    ):

        if text == "بدون شرح":

            description = None

        else:

            description = text

        context.user_data[
            "new_photo_description"
        ] = description

        context.user_data.pop(
            "waiting_for_photo_description"
        )

        context.user_data[
            "waiting_for_photo"
        ] = True

        await update.message.reply_text(
            "🖼️ الآن أرسل الصورة:"
        )

        return

    # =====================================================
    # استقبال الصورة
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_photo"
    ):

        if not update.message.photo:

            await update.message.reply_text(
                "❌ أرسل صورة من فضلك."
            )

            return

        photo = update.message.photo[-1]

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "new_photo_title"
        )

        description = context.user_data.get(
            "new_photo_description"
        )

        save_content(
            menu_id=menu_id,
            title=title,
            content_type="photo",
            file_id=photo.file_id,
            caption=description,
            description=description
        )

        context.user_data.pop(
            "waiting_for_photo"
        )

        context.user_data.pop(
            "new_photo_title",
            None
        )

        context.user_data.pop(
            "new_photo_description",
            None
        )

        await update.message.reply_text(
            "✅ تم حفظ الصورة مع شرحها.",
            reply_markup=menu_keyboard(
                menu_id
            )
        )

        return

    # =====================================================
    # إضافة فيديو
    # =====================================================

    if is_admin and text == "🎬 إضافة فيديو":

        if not context.user_data.get(
            "current_menu_id"
        ):

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "waiting_for_video_title"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل عنوان الفيديو:"
        )

        return

    # =====================================================
    # عنوان الفيديو
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_video_title"
    ):

        context.user_data[
            "new_video_title"
        ] = text

        context.user_data.pop(
            "waiting_for_video_title"
        )

        context.user_data[
            "waiting_for_video_description"
        ] = True

        await update.message.reply_text(
            "📝 أرسل شرحًا يوضح محتوى الفيديو أو اكتب:\n\nبدون شرح"
        )

        return

    # =====================================================
    # وصف الفيديو
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_video_description"
    ):

        if text == "بدون شرح":

            description = None

        else:

            description = text

        context.user_data[
            "new_video_description"
        ] = description

        context.user_data.pop(
            "waiting_for_video_description"
        )

        context.user_data[
            "waiting_for_video"
        ] = True

        await update.message.reply_text(
            "🎬 الآن أرسل الفيديو:"
        )

        return

    # =====================================================
    # استقبال الفيديو
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_video"
    ):

        if not update.message.video:

            await update.message.reply_text(
                "❌ أرسل فيديو من فضلك."
            )

            return

        video = update.message.video

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "new_video_title"
        )

        description = context.user_data.get(
            "new_video_description"
        )

        save_content(
            menu_id=menu_id,
            title=title,
            content_type="video",
            file_id=video.file_id,
            caption=description,
            description=description
        )

        context.user_data.pop(
            "waiting_for_video"
        )

        context.user_data.pop(
            "new_video_title",
            None
        )

        context.user_data.pop(
            "new_video_description",
            None
        )

        await update.message.reply_text(
            "✅ تم حفظ الفيديو مع شرحه.",
            reply_markup=menu_keyboard(
                menu_id
            )
        )

        return

    # =====================================================
    # إضافة صوت
    # =====================================================

    if is_admin and text == "🎵 إضافة صوت":

        if not context.user_data.get(
            "current_menu_id"
        ):

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "waiting_for_audio_title"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل عنوان الصوت:"
        )

        return

    # =====================================================
    # عنوان الصوت
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_audio_title"
    ):

        context.user_data[
            "new_audio_title"
        ] = text

        context.user_data.pop(
            "waiting_for_audio_title"
        )

        context.user_data[
            "waiting_for_audio_description"
        ] = True

        await update.message.reply_text(
            "📝 أرسل شرحًا للصوت أو اكتب:\n\nبدون شرح"
        )

        return

    # =====================================================
    # وصف الصوت
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_audio_description"
    ):

        if text == "بدون شرح":

            description = None

        else:

            description = text

        context.user_data[
            "new_audio_description"
        ] = description

        context.user_data.pop(
            "waiting_for_audio_description"
        )

        context.user_data[
            "waiting_for_audio"
        ] = True

        await update.message.reply_text(
            "🎵 الآن أرسل الصوت:"
        )

        return

    # =====================================================
    # استقبال الصوت
    # =====================================================

    if is_admin and context.user_data.get(
        "waiting_for_audio"
    ):

        if not update.message.audio:

            await update.message.reply_text(
                "❌ أرسل ملف صوتي من فضلك."
            )

            return

        audio = update.message.audio

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "new_audio_title"
        )

        description = context.user_data.get(
            "new_audio_description"
        )

        save_content(
            menu_id=menu_id,
            title=title,
            content_type="audio",
            file_id=audio.file_id,
            caption=description,
            description=description
        )

        context.user_data.pop(
            "waiting_for_audio"
        )

        context.user_data.pop(
            "new_audio_title",
            None
        )

        context.user_data.pop(
            "new_audio_description",
            None
        )

        await update.message.reply_text(
            "✅ تم حفظ الصوت مع شرحه.",
            reply_markup=menu_keyboard(
                menu_id
            )
        )

        return

    # =====================================================
    # فتح قائمة
    # =====================================================

    if text.startswith("📂 "):

        menu_name = text[2:].strip()

        menu = find_menu(menu_name)

        if menu:

            await show_menu(
                update,
                context,
                menu["id"]
            )

        return

    # =====================================================
    # فتح المحتوى
    # =====================================================

    content = find_content(text)

    if content:

        await send_content(
            update,
            content
        )

        return

    # =====================================================
    # الأزرار العامة
    # =====================================================

    if text in [
        "📖 القرآن والثقافة",
        "📚 الملازم",
        "🎧 المحاضرات",
        "ℹ️ عن البوت",
    ]:

        await update.message.reply_text(
            "📌 سيتم إضافة المحتوى هنا."
        )

        return


# =========================================================
# تشغيل البوت
# =========================================================

def main():

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN غير موجود."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # -----------------------------
    # الأوامر
    # -----------------------------

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

    # -----------------------------
    # الرسائل النصية
    # -----------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    # -----------------------------
    # الصور والفيديو والصوت
    # -----------------------------

    app.add_handler(
        MessageHandler(
            filters.PHOTO
            | filters.VIDEO
            | filters.AUDIO,
            handle_message
        )
    )

    print(
        "🤖 Huda People Bot is running..."
    )

    app.run_polling()


# =========================================================
# بدء التشغيل
# =========================================================

if __name__ == "__main__":
    main()
