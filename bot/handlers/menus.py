from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import get_connection, next_display_order
from bot.keyboards import admin_keyboard


def clean_menu_name(text):
    if text.startswith("📂 "):
        return text[3:].strip()
    return text.strip()


async def show_menu(update, context, menu_id):
    connection = get_connection()

    menu = connection.execute(
        """
        SELECT id, name, parent_id
        FROM menus
        WHERE id = ?
        """,
        (menu_id,),
    ).fetchone()

    if not menu:
        connection.close()
        await update.message.reply_text("❌ القائمة غير موجودة.")
        return

    context.user_data["current_menu_id"] = menu["id"]
    context.user_data["current_menu_name"] = menu["name"]

    items = []

    # الفروع
    children = connection.execute(
        """
        SELECT id, name, display_order
        FROM menus
        WHERE parent_id = ?
        ORDER BY
            CASE WHEN display_order IS NULL THEN 1 ELSE 0 END,
            display_order,
            id
        """,
        (menu_id,),
    ).fetchall()

    for child in children:
        items.append(
            (
                child["display_order"],
                f"📂 {child['name']}",
                "menu",
                child["id"],
            )
        )

    # المحتويات
    contents = connection.execute(
        """
        SELECT id, title, content_type, display_order
        FROM contents
        WHERE menu_id = ?
        ORDER BY
            CASE WHEN display_order IS NULL THEN 1 ELSE 0 END,
            display_order,
            id
        """,
        (menu_id,),
    ).fetchall()

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
                "content",
                content["id"],
            )
        )

    # مجموعات الوسائط
    groups = connection.execute(
        """
        SELECT id, title, display_order
        FROM media_groups
        WHERE menu_id = ?
        ORDER BY
            CASE WHEN display_order IS NULL THEN 1 ELSE 0 END,
            display_order,
            id
        """,
        (menu_id,),
    ).fetchall()

    for group in groups:
        items.append(
            (
                group["display_order"],
                f"🖼️🎥🎧 {group['title']}",
                "group",
                group["id"],
            )
        )

    connection.close()

    items.sort(
        key=lambda item: (
            item[0] is None,
            item[0] if item[0] is not None else 999999,
        )
    )

    keyboard = []

    for _, label, _, _ in items:
        keyboard.append([label])

    # أزرار الإدارة تظهر فقط للمشرف
    from bot.database import is_admin

    if is_admin(update.effective_user.id):
        keyboard.extend(
            [
                ["➕ إضافة فرع"],
                ["➕ إضافة محتوى"],
                ["✏️ تعديل المحتوى"],
                ["🗑️ حذف المحتوى"],
                ["↕️ ترتيب العناصر"],
            ]
        )

    # زر الرجوع موجود دائمًا
    keyboard.append(["◀️ رجوع"])

    await update.message.reply_text(
        f"📂 {menu['name']}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


async def create_root_menu(update, context, name):
    name = name.strip()

    if not name:
        await update.message.reply_text(
            "❌ اسم القائمة لا يمكن أن يكون فارغًا."
        )
        return

    connection = get_connection()

    existing = connection.execute(
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

    display_order = connection.execute(
        """
        SELECT COALESCE(MAX(display_order), -1) + 1
        FROM menus
        WHERE parent_id IS NULL
        """
    ).fetchone()[0]

    cursor = connection.cursor()

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

    new_menu_id = cursor.lastrowid

    connection.commit()
    connection.close()

    await update.message.reply_text(
        f"✅ تم إنشاء القائمة الرئيسية:\n\n"
        f"📂 {name}"
    )

    await show_menu(
        update,
        context,
        new_menu_id,
    )


async def create_child_menu(update, context, parent_id, name):
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

    existing = connection.execute(
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

    display_order = next_display_order(parent_id)

    sort_order = connection.execute(
        """
        SELECT COALESCE(MAX(sort_order), -1) + 1
        FROM menus
        WHERE parent_id = ?
        """,
        (parent_id,),
    ).fetchone()[0]

    cursor = connection.cursor()

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

    new_menu_id = cursor.lastrowid

    connection.commit()
    connection.close()

    await update.message.reply_text(
        f"✅ تم إنشاء الفرع:\n\n"
        f"📂 {name}"
    )

    await show_menu(
        update,
        context,
        new_menu_id,
    )


async def go_back_one_level(update, context):
    current_menu_id = context.user_data.get(
        "current_menu_id"
    )

    if not current_menu_id:
        await update.message.reply_text(
            "⚙️ لوحة إدارة البوت",
            reply_markup=admin_keyboard(),
        )
        return

    connection = get_connection()

    current_menu = connection.execute(
        """
        SELECT id, name, parent_id
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

    parent_id = current_menu["parent_id"]

    # إذا كانت قائمة فرعية، ارجع للأب
    if parent_id is not None:
        await show_menu(
            update,
            context,
            parent_id,
        )
        return

    # إذا كانت قائمة رئيسية، ارجع إلى لوحة الإدارة
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
