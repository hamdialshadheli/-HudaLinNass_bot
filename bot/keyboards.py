from telegram import ReplyKeyboardMarkup


def make_keyboard(rows):
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


def admin_keyboard():
    return make_keyboard([
        ["➕ إنشاء قائمة", "📋 إدارة القوائم"],
        ["➕ إضافة محتوى", "✏️ تعديل المحتوى"],
        ["🗑️ حذف المحتوى", "↕️ ترتيب العناصر"],
        ["👥 المشرفون", "📊 الإحصائيات"],
        ["🏠 القائمة الرئيسية"],
    ])


def menu_management_keyboard():
    return make_keyboard([
        ["➕ إضافة فرع"],
        ["➕ إضافة محتوى", "✏️ تعديل المحتوى"],
        ["🗑️ حذف المحتوى", "↕️ ترتيب العناصر"],
        ["◀️ رجوع"],
    ])


def content_type_keyboard():
    return make_keyboard([
        ["📝 نص", "🖼️ صورة"],
        ["🎥 فيديو", "🎧 صوت"],
        ["📄 ملف", "🔗 رابط"],
        ["🖼️🎥🎧 مجموعة وسائط"],
        ["◀️ رجوع"],
    ])


def cancel_keyboard():
    return make_keyboard([
        ["❌ إلغاء"],
    ])


def confirm_delete_keyboard():
    return make_keyboard([
        ["✅ نعم، حذف"],
        ["❌ إلغاء"],
    ])


def back_keyboard():
    return make_keyboard([
        ["◀️ رجوع"],
    ])


def menu_navigation_keyboard(items):
    rows = []

    for item in items:
        rows.append([item])

    rows.append(["◀️ رجوع"])

    return make_keyboard(rows)
