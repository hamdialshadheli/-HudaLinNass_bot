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
# لوحة المستخدم
# =========================================================

MAIN_KEYBOARD = [
    ["📖 القرآن والثقافة"],
    ["📚 الملازم"],
    ["🎧 المحاضرات"],
    ["ℹ️ عن البوت"],
]

# =========================================================
# لوحة الإدارة
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
# أيقونة نوع المجموعة
# =========================================================

def media_group_icon(media_type):

    icons = {
        "photo": "🖼️",
        "video": "🎬",
        "audio": "🎵",
    }

    return icons.get(
        media_type,
        "📦"
    )

# =========================================================
# إزالة أيقونة الزر
# =========================================================

def remove_button_icon(text):

    icons = [
        "📝 ",
        "🖼️ ",
        "🎬 ",
        "🎵 ",
        "📄 ",
    ]

    for icon in icons:

        if text.startswith(icon):

            return text[len(icon):]

    return text

# =========================================================
# لوحة القائمة
# =========================================================

def menu_keyboard(menu_id):

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # الفروع
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # المحتويات الفردية
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # مجموعات الوسائط
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT id, title, media_type
        FROM media_groups
        WHERE menu_id = ?
        ORDER BY sort_order, id
        """,
        (menu_id,)
    )

    groups = cursor.fetchall()

    connection.close()

    keyboard = []

    # -----------------------------------------------------
    # الفروع
    # -----------------------------------------------------

    for menu in menus:

        keyboard.append(
            [f"📂 {menu['name']}"]
        )

    # -----------------------------------------------------
    # المحتويات الفردية
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # مجموعات الوسائط
    # -----------------------------------------------------

    for group in groups:

        icon = media_group_icon(
            group["media_type"]
        )

        keyboard.append(
            [f"{icon} {group['title']}"]
        )

    # -----------------------------------------------------
    # أزرار الإدارة
    # -----------------------------------------------------

    keyboard.extend(
        [
            ["➕ إضافة فرع"],
            ["📝 إضافة نص"],
            ["🖼️ إضافة صور متعددة"],
            ["🎬 إضافة فيديوهات متعددة"],
            ["🎵 إضافة أصوات متعددة"],
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
    update,
    context,
    menu_id,
    add_to_stack=True
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

    # -----------------------------------------------------
    # حفظ القائمة الحالية
    # -----------------------------------------------------

    context.user_data[
        "current_menu_id"
    ] = menu["id"]

    context.user_data[
        "current_menu_name"
    ] = menu["name"]

    # -----------------------------------------------------
    # إدارة مسار القوائم
    # -----------------------------------------------------

    if add_to_stack:

        stack = context.user_data.get(
            "menu_stack",
            []
        )

        # منع تكرار نفس القائمة في المسار
        if not stack or stack[-1] != menu["id"]:

            stack.append(
                menu["id"]
            )

        context.user_data[
            "menu_stack"
        ] = stack

    # -----------------------------------------------------
    # عرض القائمة
    # -----------------------------------------------------

    await update.message.reply_text(
        f"📂 {menu['name']}",
        reply_markup=menu_keyboard(
            menu["id"]
        )
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

    user_id = str(
        update.effective_user.id
    )

    if user_id != str(ADMIN_ID):

        await update.message.reply_text(
            "❌ ليس لديك صلاحية الدخول."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ لوحة إدارة البوت",
        reply_markup=admin_keyboard()
    )

# =========================================================
# إنشاء مجموعة وسائط
# =========================================================

def create_media_group(
    menu_id,
    title,
    description,
    media_type
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO media_groups (
            menu_id,
            title,
            description,
            media_type
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            menu_id,
            title,
            description,
            media_type
        )
    )

    group_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return group_id

# =========================================================
# إضافة ملف إلى مجموعة
# =========================================================

def add_media_item(
    group_id,
    file_id,
    caption=None
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM media_group_items
        WHERE group_id = ?
        """,
        (group_id,)
    )

    result = cursor.fetchone()

    sort_order = result["total"]

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
            sort_order
        )
    )

    connection.commit()
    connection.close()

# =========================================================
# حفظ نص
# =========================================================

def save_text(
    menu_id,
    title,
    text_content
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO contents (
            menu_id,
            title,
            content_type,
            text_content
        )
        VALUES (?, ?, 'text', ?)
        """,
        (
            menu_id,
            title,
            text_content
        )
    )

    connection.commit()
    connection.close()

# =========================================================
# إرسال محتوى فردي
# =========================================================

async def send_single_content(
    update,
    content
):

    description = content["description"]

    # -----------------------------------------------------
    # النص
    # -----------------------------------------------------

    if content["content_type"] == "text":

        message = (
            content["text_content"]
            or ""
        )

        if description:

            message = (
                f"📝 {content['title']}\n\n"
                f"{description}\n\n"
                f"{message}"
            )

        await update.message.reply_text(
            message
        )

    # -----------------------------------------------------
    # الصورة
    # -----------------------------------------------------

    elif content["content_type"] == "photo":

        caption = (
            f"🖼️ {content['title']}"
        )

        if description:

            caption += (
                f"\n\n📝 {description}"
            )

        await update.message.reply_photo(
            photo=content["file_id"],
            caption=caption
        )

    # -----------------------------------------------------
    # الفيديو
    # -----------------------------------------------------

    elif content["content_type"] == "video":

        caption = (
            f"🎬 {content['title']}"
        )

        if description:

            caption += (
                f"\n\n📝 {description}"
            )

        await update.message.reply_video(
            video=content["file_id"],
            caption=caption
        )

    # -----------------------------------------------------
    # الصوت
    # -----------------------------------------------------

    elif content["content_type"] == "audio":

        caption = (
            f"🎵 {content['title']}"
        )

        if description:

            caption += (
                f"\n\n📝 {description}"
            )

        await update.message.reply_audio(
            audio=content["file_id"],
            caption=caption
        )

# =========================================================
# إرسال مجموعة وسائط
# =========================================================

async def send_media_group(
    update,
    group
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM media_group_items
        WHERE group_id = ?
        ORDER BY sort_order, id
        """,
        (group["id"],)
    )

    items = cursor.fetchall()

    connection.close()

    if not items:

        await update.message.reply_text(
            "❌ هذه المجموعة لا تحتوي على ملفات."
        )

        return

    # -----------------------------------------------------
    # الوصف
    # -----------------------------------------------------

    if group["description"]:

        await update.message.reply_text(
            f"📌 {group['title']}\n\n"
            f"📝 {group['description']}"
        )

    # -----------------------------------------------------
    # الصور
    # -----------------------------------------------------

    if group["media_type"] == "photo":

        for item in items:

            await update.message.reply_photo(
                photo=item["file_id"]
            )

    # -----------------------------------------------------
    # الفيديوهات
    # -----------------------------------------------------

    elif group["media_type"] == "video":

        for item in items:

            await update.message.reply_video(
                video=item["file_id"]
            )

    # -----------------------------------------------------
    # الأصوات
    # -----------------------------------------------------

    elif group["media_type"] == "audio":

        for item in items:

            await update.message.reply_audio(
                audio=item["file_id"]
            )

# =========================================================
# استقبال النصوص
# =========================================================

async def handle_text(
    update,
    context
):

    text = update.message.text

    user_id = str(
        update.effective_user.id
    )

    is_admin = (
        user_id == str(ADMIN_ID)
    )

    # =====================================================
    # إنهاء مجموعة
    # =====================================================

    if (
        is_admin
        and text == "✅ إنهاء"
        and context.user_data.get(
            "creating_media_group"
        )
    ):

        total = context.user_data.get(
            "media_group_count",
            0
        )

        if total == 0:

            await update.message.reply_text(
                "❌ لم يتم إضافة أي ملف."
            )

            return

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        context.user_data.pop(
            "creating_media_group",
            None
        )

        context.user_data.pop(
            "media_group_id",
            None
        )

        context.user_data.pop(
            "media_group_count",
            None
        )

        await update.message.reply_text(
            f"✅ تم حفظ المجموعة بنجاح.\n"
            f"📦 عدد الملفات: {total}",
            reply_markup=menu_keyboard(
                menu_id
            )
        )

        return

    # =====================================================
    # إلغاء العملية
    # =====================================================

    if (
        is_admin
        and text == "❌ إلغاء"
        and context.user_data.get(
            "creating_media_group"
        )
    ):

        context.user_data.pop(
            "creating_media_group",
            None
        )

        context.user_data.pop(
            "media_group_id",
            None
        )

        context.user_data.pop(
            "media_group_count",
            None
        )

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        await update.message.reply_text(
            "❌ تم إلغاء العملية.",
            reply_markup=menu_keyboard(
                menu_id
            )
        )

        return

    # =====================================================
    # إنشاء مجموعة صور
    # =====================================================

    if (
        is_admin
        and text == "🖼️ إضافة صور متعددة"
    ):

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not menu_id:

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "new_group_type"
        ] = "photo"

        context.user_data[
            "waiting_group_title"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل عنوان مجموعة الصور:"
        )

        return

    # =====================================================
    # إنشاء مجموعة فيديوهات
    # =====================================================

    if (
        is_admin
        and text == "🎬 إضافة فيديوهات متعددة"
    ):

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not menu_id:

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "new_group_type"
        ] = "video"

        context.user_data[
            "waiting_group_title"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل عنوان مجموعة الفيديوهات:"
        )

        return

    # =====================================================
    # إنشاء مجموعة أصوات
    # =====================================================

    if (
        is_admin
        and text == "🎵 إضافة أصوات متعددة"
    ):

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        if not menu_id:

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "new_group_type"
        ] = "audio"

        context.user_data[
            "waiting_group_title"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل عنوان مجموعة الأصوات:"
        )

        return

    # =====================================================
    # عنوان المجموعة
    # =====================================================

    if (
        is_admin
        and context.user_data.get(
            "waiting_group_title"
        )
    ):

        context.user_data[
            "new_group_title"
        ] = text

        context.user_data.pop(
            "waiting_group_title"
        )

        context.user_data[
            "waiting_group_description"
        ] = True

        await update.message.reply_text(
            "📝 أرسل شرح المجموعة، أو اكتب:\n\n"
            "بدون شرح"
        )

        return

    # =====================================================
    # وصف المجموعة
    # =====================================================

    if (
        is_admin
        and context.user_data.get(
            "waiting_group_description"
        )
    ):

        description = (
            None
            if text == "بدون شرح"
            else text
        )

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "new_group_title"
        )

        media_type = context.user_data.get(
            "new_group_type"
        )

        group_id = create_media_group(
            menu_id,
            title,
            description,
            media_type
        )

        context.user_data[
            "media_group_id"
        ] = group_id

        context.user_data[
            "media_group_count"
        ] = 0

        context.user_data[
            "creating_media_group"
        ] = True

        context.user_data.pop(
            "waiting_group_description"
        )

        keyboard = ReplyKeyboardMarkup(
            [
                ["✅ إنهاء"],
                ["❌ إلغاء"],
            ],
            resize_keyboard=True
        )

        await update.message.reply_text(
            "📤 الآن أرسل الملفات واحدًا تلو الآخر.\n\n"
            "عندما تنتهي اضغط «✅ إنهاء».",
            reply_markup=keyboard
        )

        return

    # =====================================================
    # إضافة قائمة رئيسية
    # =====================================================

    if (
        is_admin
        and text == "➕ إضافة قائمة"
    ):

        context.user_data[
            "waiting_for_menu_name"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل اسم القائمة:"
        )

        return

    # =====================================================
    # حفظ القائمة الرئيسية
    # =====================================================

    if (
        is_admin
        and context.user_data.get(
            "waiting_for_menu_name"
        )
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
            "✅ تم إنشاء القائمة.",
            reply_markup=admin_keyboard()
        )

        return

    # =====================================================
    # إدارة القوائم
    # =====================================================

    if (
        is_admin
        and text == "📋 إدارة القوائم"
    ):

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
            "📋 اختر القائمة:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )
        )

        return

    # =====================================================
    # إضافة فرع
    # =====================================================

    if (
        is_admin
        and text == "➕ إضافة فرع"
    ):

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

    if (
        is_admin
        and context.user_data.get(
            "waiting_for_branch_name"
        )
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
            "✅ تم إنشاء الفرع.",
            reply_markup=menu_keyboard(
                parent_id
            )
        )

        return

    # =====================================================
    # إضافة نص
    # =====================================================

    if (
        is_admin
        and text == "📝 إضافة نص"
    ):

        if not context.user_data.get(
            "current_menu_id"
        ):

            await update.message.reply_text(
                "❌ افتح قائمة أولًا."
            )

            return

        context.user_data[
            "waiting_text_title"
        ] = True

        await update.message.reply_text(
            "✏️ أرسل عنوان النص:"
        )

        return

    # =====================================================
    # عنوان النص
    # =====================================================

    if (
        is_admin
        and context.user_data.get(
            "waiting_text_title"
        )
    ):

        context.user_data[
            "new_text_title"
        ] = text

        context.user_data.pop(
            "waiting_text_title"
        )

        context.user_data[
            "waiting_text_content"
        ] = True

        await update.message.reply_text(
            "📝 أرسل محتوى النص:"
        )

        return

    # =====================================================
    # حفظ النص
    # =====================================================

    if (
        is_admin
        and context.user_data.get(
            "waiting_text_content"
        )
    ):

        menu_id = context.user_data.get(
            "current_menu_id"
        )

        title = context.user_data.get(
            "new_text_title"
        )

        save_text(
            menu_id,
            title,
            text
        )

        context.user_data.pop(
            "waiting_text_content"
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
    # الرجوع
    # =====================================================

    if text == "◀️ رجوع":

        # -------------------------------------------------
        # إلغاء أي عملية قيد التنفيذ
        # -------------------------------------------------

        for key in [
            "waiting_for_menu_name",
            "waiting_for_branch_name",
            "waiting_text_title",
            "waiting_text_content",
            "waiting_group_title",
            "waiting_group_description",
            "creating_media_group",
            "media_group_id",
            "media_group_count",
        ]:

            context.user_data.pop(
                key,
                None
            )

        # -------------------------------------------------
        # استخدام مسار القوائم
        # -------------------------------------------------

        stack = context.user_data.get(
            "menu_stack",
            []
        )

        # -------------------------------------------------
        # إذا كان لدينا أكثر من قائمة في المسار
        # -------------------------------------------------

        if len(stack) > 1:

            # إزالة القائمة الحالية
            stack.pop()

            # الأب المباشر
            parent_id = stack[-1]

            context.user_data[
                "menu_stack"
            ] = stack

            await show_menu(
                update,
                context,
                parent_id,
                add_to_stack=False
            )

            return

        # -------------------------------------------------
        # إذا كنا في أول قائمة
        # -------------------------------------------------

        context.user_data.pop(
            "current_menu_id",
            None
        )

        context.user_data.pop(
            "current_menu_name",
            None
        )

        context.user_data.pop(
            "menu_stack",
            None
        )

        await update.message.reply_text(
            "⚙️ لوحة إدارة البوت",
            reply_markup=admin_keyboard()
        )

        return

    # =====================================================
    # فتح قائمة
    # =====================================================

    if text.startswith("📂 "):

        menu_name = text[
            len("📂 "):
        ].strip()

        current_menu_id = context.user_data.get(
            "current_menu_id"
        )

        connection = get_connection()
        cursor = connection.cursor()

        # -------------------------------------------------
        # إذا كنا داخل قائمة، ابحث فقط عن أبنائها
        # -------------------------------------------------

        if current_menu_id:

            cursor.execute(
                """
                SELECT *
                FROM menus
                WHERE name = ?
                AND parent_id = ?
                LIMIT 1
                """,
                (
                    menu_name,
                    current_menu_id
                )
            )

        else:

            # -------------------------------------------------
            # القوائم الرئيسية فقط
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT *
                FROM menus
                WHERE name = ?
                AND parent_id IS NULL
                LIMIT 1
                """,
                (menu_name,)
            )

        menu = cursor.fetchone()

        connection.close()

        if menu:

            await show_menu(
                update,
                context,
                menu["id"]
            )

        return

    # =====================================================
    # فتح مجموعة وسائط
    # =====================================================

    group_title = remove_button_icon(
        text
    )

    connection = get_connection()
    cursor = connection.cursor()

    current_menu_id = context.user_data.get(
        "current_menu_id"
    )

    # -----------------------------------------------------
    # البحث داخل القائمة الحالية
    # -----------------------------------------------------

    if current_menu_id:

        cursor.execute(
            """
            SELECT *
            FROM media_groups
            WHERE title = ?
            AND menu_id = ?
            LIMIT 1
            """,
            (
                group_title,
                current_menu_id
            )
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM media_groups
            WHERE title = ?
            LIMIT 1
            """,
            (group_title,)
        )

    group = cursor.fetchone()

    connection.close()

    if group:

        await send_media_group(
            update,
            group
        )

        return

    # =====================================================
    # فتح محتوى فردي
    # =====================================================

    content_title = remove_button_icon(
        text
    )

    connection = get_connection()
    cursor = connection.cursor()

    current_menu_id = context.user_data.get(
        "current_menu_id"
    )

    # -----------------------------------------------------
    # البحث داخل القائمة الحالية
    # -----------------------------------------------------

    if current_menu_id:

        cursor.execute(
            """
            SELECT *
            FROM contents
            WHERE title = ?
            AND menu_id = ?
            LIMIT 1
            """,
            (
                content_title,
                current_menu_id
            )
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM contents
            WHERE title = ?
            LIMIT 1
            """,
            (content_title,)
        )

    content = cursor.fetchone()

    connection.close()

    if content:

        await send_single_content(
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

# =========================================================
# استقبال الملفات
# =========================================================

async def handle_media(
    update,
    context
):

    user_id = str(
        update.effective_user.id
    )

    is_admin = (
        user_id == str(ADMIN_ID)
    )

    if not is_admin:
        return

    if not context.user_data.get(
        "creating_media_group"
    ):

        await update.message.reply_text(
            "❌ لا توجد عملية إضافة ملفات قيد التنفيذ."
        )

        return

    group_id = context.user_data.get(
        "media_group_id"
    )

    media_type = context.user_data.get(
        "new_group_type"
    )

    file_id = None

    # -----------------------------------------------------
    # صورة
    # -----------------------------------------------------

    if update.message.photo:

        if media_type != "photo":

            await update.message.reply_text(
                "❌ هذه المجموعة مخصصة لنوع آخر من الملفات."
            )

            return

        file_id = update.message.photo[
            -1
        ].file_id

    # -----------------------------------------------------
    # فيديو
    # -----------------------------------------------------

    elif update.message.video:

        if media_type != "video":

            await update.message.reply_text(
                "❌ هذه المجموعة مخصصة لنوع آخر من الملفات."
            )

            return

        file_id = update.message.video.file_id

    # -----------------------------------------------------
    # صوت
    # -----------------------------------------------------

    elif update.message.audio:

        if media_type != "audio":

            await update.message.reply_text(
                "❌ هذه المجموعة مخصصة لنوع آخر من الملفات."
            )

            return

        file_id = update.message.audio.file_id

    # -----------------------------------------------------
    # حفظ الملف
    # -----------------------------------------------------

    if file_id:

        add_media_item(
            group_id,
            file_id
        )

        count = context.user_data.get(
            "media_group_count",
            0
        ) + 1

        context.user_data[
            "media_group_count"
        ] = count

        await update.message.reply_text(
            f"✅ تم حفظ الملف رقم {count}.\n"
            f"📤 يمكنك إرسال الملف التالي أو الضغط على «✅ إنهاء»."
        )

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

    # -----------------------------------------------------
    # /start
    # -----------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # -----------------------------------------------------
    # /admin
    # -----------------------------------------------------

    app.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )

    # -----------------------------------------------------
    # النصوص
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    # -----------------------------------------------------
    # الصور
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_media
        )
    )

    # -----------------------------------------------------
    # الفيديو
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.VIDEO,
            handle_media
        )
    )

    # -----------------------------------------------------
    # الأصوات
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.AUDIO,
            handle_media
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
