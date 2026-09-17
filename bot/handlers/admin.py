from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import (
    get_connection,
    is_admin,
    add_admin,
    remove_admin,
)

from bot.keyboards import (
    admin_keyboard,
    cancel_keyboard,
)


# ==========================================
# التحقق من صلاحية المشرف
# ==========================================

def check_admin(update):
    user = update.effective_user

    if not user:
        return False

    return is_admin(user.id)


# ==========================================
# قائمة المشرفين
# ==========================================

async def show_admins(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not check_admin(update):

        await update.message.reply_text(
            "⛔ ليس لديك صلاحية المشرف."
        )

        return

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT user_id, added_at
        FROM admins
        ORDER BY added_at, user_id
        """
    ).fetchall()

    connection.close()

    text = "👥 المشرفون الحاليون:\n\n"

    if not rows:

        text += "لا يوجد مشرفون."

    else:

        for index, row in enumerate(rows, start=1):

            text += (
                f"{index}. "
                f"`{row['user_id']}`\n"
            )

    keyboard = ReplyKeyboardMarkup(
        [
            ["➕ إضافة مشرف"],
            ["🗑️ حذف مشرف"],
            ["◀️ رجوع"],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


# ==========================================
# إضافة مشرف
# ==========================================

async def start_add_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not check_admin(update):
        return

    context.user_data[
        "waiting_for_admin_id"
    ] = True

    await update.message.reply_text(
        "👤 أرسل Telegram User ID للمشرف الجديد:\n\n"
        "مثال:\n"
        "123456789",
        reply_markup=cancel_keyboard(),
    )


async def receive_admin_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not check_admin(update):
        return

    value = (
        update.message.text
        or ""
    ).strip()

    try:

        user_id = int(value)

    except ValueError:

        await update.message.reply_text(
            "❌ معرف المستخدم يجب أن يكون رقمًا فقط."
        )

        return

    if user_id <= 0:

        await update.message.reply_text(
            "❌ معرف المستخدم غير صحيح."
        )

        return

    add_admin(user_id)

    context.user_data.pop(
        "waiting_for_admin_id",
        None,
    )

    await update.message.reply_text(
        f"✅ تمت إضافة المشرف بنجاح.\n\n"
        f"User ID: {user_id}",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["➕ إضافة مشرف"],
                ["🗑️ حذف مشرف"],
                ["◀️ رجوع"],
            ],
            resize_keyboard=True,
        ),
    )


# ==========================================
# حذف مشرف
# ==========================================

async def start_remove_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not check_admin(update):
        return

    await update.message.reply_text(
        "🗑️ أرسل User ID للمشرف الذي تريد حذفه:",
        reply_markup=cancel_keyboard(),
    )

    context.user_data[
        "waiting_for_remove_admin_id"
    ] = True


async def receive_remove_admin_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not check_admin(update):
        return

    value = (
        update.message.text
        or ""
    ).strip()

    try:

        user_id = int(value)

    except ValueError:

        await update.message.reply_text(
            "❌ معرف المستخدم يجب أن يكون رقمًا فقط."
        )

        return

    # ======================================
    # حماية المشرف الأساسي
    # ======================================

    import os

    primary_admin = int(
        os.getenv(
            "ADMIN_ID",
            "0",
        )
    )

    if user_id == primary_admin:

        await update.message.reply_text(
            "⛔ لا يمكن حذف المشرف الأساسي "
            "الموجود في GitHub Secrets."
        )

        return

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT user_id
        FROM admins
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    connection.close()

    if not existing:

        await update.message.reply_text(
            "⚠️ هذا المستخدم ليس مشرفًا."
        )

        return

    remove_admin(user_id)

    context.user_data.pop(
        "waiting_for_remove_admin_id",
        None,
    )

    await update.message.reply_text(
        f"🗑️ تم حذف المشرف:\n\n"
        f"{user_id}",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["➕ إضافة مشرف"],
                ["🗑️ حذف مشرف"],
                ["◀️ رجوع"],
            ],
            resize_keyboard=True,
        ),
    )


# ==========================================
# الإحصائيات
# ==========================================

async def show_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not check_admin(update):

        await update.message.reply_text(
            "⛔ ليس لديك صلاحية المشرف."
        )

        return

    connection = get_connection()

    users_count = connection.execute(
        """
        SELECT COUNT(*)
        AS count
        FROM users
        """
    ).fetchone()["count"]

    admins_count = connection.execute(
        """
        SELECT COUNT(*)
        AS count
        FROM admins
        """
    ).fetchone()["count"]

    menus_count = connection.execute(
        """
        SELECT COUNT(*)
        AS count
        FROM menus
        """
    ).fetchone()["count"]

    contents_count = connection.execute(
        """
        SELECT COUNT(*)
        AS count
        FROM contents
        """
    ).fetchone()["count"]

    groups_count = connection.execute(
        """
        SELECT COUNT(*)
        AS count
        FROM media_groups
        """
    ).fetchone()["count"]

    total_views = connection.execute(
        """
        SELECT COALESCE(
            SUM(views),
            0
        )
        AS total
        FROM content_stats
        """
    ).fetchone()["total"]

    connection.close()

    message = (
        "📊 إحصائيات البوت\n\n"
        f"👥 المستخدمون: {users_count}\n"
        f"🛡️ المشرفون: {admins_count}\n"
        f"📂 القوائم والفروع: {menus_count}\n"
        f"📝 المحتويات: {contents_count}\n"
        f"🖼️🎥🎧 مجموعات الوسائط: {groups_count}\n"
        f"👁️ مشاهدات المحتوى: {total_views}"
    )

    await update.message.reply_text(
        message,
        reply_markup=admin_keyboard(),
    )
