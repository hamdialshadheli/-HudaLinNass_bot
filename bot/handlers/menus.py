from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import (
    get_connection,
    next_display_order,
)

from bot.keyboards import (
    admin_keyboard,
)


# ==========================================
# إزالة رمز المجلد من اسم الزر
# ==========================================

def clean_menu_name(text):
    if text.startswith("📂 "):
        return text[3:].strip()

    return text.strip()


# ==========================================
# عرض قائمة معينة
# ==========================================

async def show_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    menu_id: int,
):

    connection = get_connection()
    cursor = connection.cursor()

    # جلب القائمة الحالية
    menu = cursor.execute(
        """
        SELECT *
        FROM menus
        WHERE id = ?
        """,
        (menu_id,),
    ).fetchone()

    if not menu:
        connection.close()

        await update.message.reply_text(
            "❌ القائمة غير موجودة."
        )

        return

    # حفظ القائمة الحالية
    context.user_data["current_menu_id"] = menu_id
    context.user_data["current_menu_name"] = menu["name"]

    items = []

    # ======================================
    # الفروع
    # ======================================

    cursor.execute(
        """
        SELECT
            id,
            name,
            display_order
        FROM menus
        WHERE parent_id = ?
        ORDER BY display_order, id
        """,
        (menu_id,),
    )

    children = cursor.fetchall()

    for child in children:

        items.append(
            (
                child["display_order"],
                f"📂 {child['name']}",
            )
        )

    # ======================================
    # المحتوى
    # ======================================

    cursor.execute(
        """
        SELECT
            id,
            title,
            content_type,
            display_order
        FROM contents
        WHERE menu_id = ?
        ORDER BY display_order, id
        """,
        (menu_id,),
    )

    contents = cursor.fetchall()

    content_icons = {
        "text": "📝",
        "photo": "🖼️",
        "video": "🎥",
        "audio": "🎧",
        "document": "📄",
        "link": "🔗",
    }

    for content in contents:

        icon = content_icons.get(
            content["content_type"],
            "📌",
        )

        items.append(
            (
                content["display_order"],
                f"{icon} {content['title']}",
            )
        )

    # ======================================
    # مجموعات الوسائط
    # ======================================

    cursor.execute(
        """
        SELECT
            id,
            title,
            display_order
        FROM media_groups
        WHERE menu_id = ?
        ORDER BY display_order, id
        """,
        (menu_id,),
    )

    groups = cursor.fetchall()

    for group in groups:

        items.append(
            (
                group["display_order"],
                f"🖼️🎥🎧 {group['title']}",
            )
        )

    connection.close()

    # ======================================
    # ترتيب جميع العناصر
    # ======================================

    items.sort(
        key=lambda item: (
            item[0] is None,
            item[0]
            if item[0] is not None
            else 999999,
        )
    )

    # ======================================
    # إنشاء لوحة الأزرار
    # ======================================

    keyboard = []

    for _, label in items:

        keyboard.append(
            [label]
        )

    # زر الرجوع
    keyboard.append(
        ["◀️ رجوع"]
    )

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        f"📂 {menu['name']}",
        reply_markup=reply_markup,
    )


# ==========================================
# إنشاء قائمة رئيسية
# ==========================================

async def create_root_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    name: str,
):

    name = name.strip()

    if not name:

        await update.message.reply_text(
            "❌ اسم القائمة لا يمكن أن يكون فارغًا."
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    # التأكد من عدم تكرار الاسم
    existing = cursor.execute(
        """
        SELECT id
        FROM menus
        WHERE name = ?
        AND parent_id IS NULL
        LIMIT 1
        """,
        (name,),
    ).fetchone()

    if existing:

        connection.close()

        await update.message.reply_text(
            "⚠️ توجد قائمة رئيسية بهذا الاسم بالفعل."
        )

        return

    # تحديد الترتيب
    cursor.execute(
        """
        SELECT COALESCE(
            MAX(display_order),
            -1
        ) + 1 AS next_order
        FROM menus
        WHERE parent_id IS NULL
        """
    )

    display_order = cursor.fetchone()["next_order"]

    # إنشاء القائمة
    cursor.execute(
        """
        INSERT INTO menus (
            name,
            parent_id,
            sort_order,
            display_order
        )
        VALUES (?, NULL, ?, ?)
        """,
        (
            name,
            display_order,
            display_order,
        ),
    )

    connection.commit()

    new_menu_id = cursor.lastrowid

    connection.close()

    # فتح القائمة الجديدة مباشرة
    context.user_data["current_menu_id"] = new_menu_id
    context.user_data["current_menu_name"] = name

    await update.message.reply_text(
        f"✅ تم إنشاء القائمة الرئيسية:\n\n📂 {name}"
    )

    await show_menu(
        update,
        context,
        new_menu_id,
    )


# ==========================================
# إنشاء فرع داخل القائمة الحالية
# ==========================================

async def create_child_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    parent_id: int,
    name: str,
):

    name = name.strip()

    if not name:

        await update.message.reply_text(
            "❌ اسم الفرع لا يمكن أن يكون فارغًا."
        )

        return

    if not parent_id:

        await update.message.reply_text(
            "❌ لم يتم تحديد القائمة الأب."
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    # التأكد من عدم تكرار الفرع داخل نفس الأب
    existing = cursor.execute(
        """
        SELECT id
        FROM menus
        WHERE name = ?
        AND parent_id = ?
        LIMIT 1
        """,
        (
            name,
            parent_id,
        ),
    ).fetchone()

    if existing:

        connection.close()

        await update.message.reply_text(
            "⚠️ يوجد فرع بهذا الاسم داخل هذه القائمة بالفعل."
        )

        return

    # ترتيب العنصر الجديد
    display_order = next_display_order(
        parent_id
    )

    cursor.execute(
        """
        SELECT COALESCE(
            MAX(sort_order),
            -1
        ) + 1 AS next_order
        FROM menus
        WHERE parent_id = ?
        """,
        (parent_id,),
    )

    sort_order = cursor.fetchone()["next_order"]

    # إنشاء الفرع
    cursor.execute(
        """
        INSERT INTO menus (
            name,
            parent_id,
            sort_order,
            display_order
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            parent_id,
            sort_order,
            display_order,
        ),
    )

    connection.commit()

    new_menu_id = cursor.lastrowid

    connection.close()

    await update.message.reply_text(
        f"✅ تم إنشاء الفرع:\n\n📂 {name}"
    )

    # فتح الفرع مباشرة
    await show_menu(
        update,
        context,
        new_menu_id,
    )


# ==========================================
# الرجوع درجة واحدة فقط
# ==========================================

async def go_back_one_level(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    current_menu_id = context.user_data.get(
        "current_menu_id"
    )

    # إذا لم نكن داخل قائمة
    if not current_menu_id:

        await update.message.reply_text(
            "⚙️ لوحة إدارة البوت",
            reply_markup=admin_keyboard(),
        )

        return

    connection = get_connection()

    current_menu = connection.execute(
        """
        SELECT
            id,
            name,
            parent_id
        FROM menus
        WHERE id = ?
        """,
        (current_menu_id,),
    ).fetchone()

    connection.close()

    if not current_menu:

        context.user_data.pop(
            "current_menu_id",
            None,
        )

        context.user_data.pop(
            "current_menu_name",
            None,
        )

        await update.message.reply_text(
            "⚙️ لوحة إدارة البوت",
            reply_markup=admin_keyboard(),
        )

        return

    # ======================================
    # إذا كان هناك أب
    # ======================================

    if current_menu["parent_id"] is not None:

        await show_menu(
            update,
            context,
            current_menu["parent_id"],
        )

        return

    # ======================================
    # إذا كانت قائمة رئيسية
    # ======================================

    context.user_data.pop(
        "current_menu_id",
        None,
    )

    context.user_data.pop(
        "current_menu_name",
        None,
    )

    await update.message.reply_text(
        "⚙️ لوحة إدارة البوت",
        reply_markup=admin_keyboard(),
    )
