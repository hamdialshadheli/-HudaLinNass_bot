import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data") / "huda.db"


def get_connection():
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    # =========================
    # القوائم
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            display_order INTEGER,
            FOREIGN KEY (parent_id)
            REFERENCES menus(id)
        )
    """)

    # =========================
    # المحتوى
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL,
            text_content TEXT,
            file_id TEXT,
            caption TEXT,
            description TEXT,
            url TEXT,
            sort_order INTEGER DEFAULT 0,
            display_order INTEGER,
            FOREIGN KEY (menu_id)
            REFERENCES menus(id)
        )
    """)

    # =========================
    # مجموعات الوسائط
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            media_type TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            display_order INTEGER,
            FOREIGN KEY (menu_id)
            REFERENCES menus(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_group_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            caption TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (group_id)
            REFERENCES media_groups(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # المشرفون
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # المستخدمون
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # إحصائيات المحتوى
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_stats (
            content_id INTEGER PRIMARY KEY,
            views INTEGER DEFAULT 0
        )
    """)

    # =========================
    # إحصائيات القوائم
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_stats (
            menu_id INTEGER PRIMARY KEY,
            views INTEGER DEFAULT 0
        )
    """)

    # =========================
    # إضافة أعمدة للنسخ القديمة
    # =========================

    cursor.execute("PRAGMA table_info(contents)")

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "description" not in columns:
        cursor.execute("""
            ALTER TABLE contents
            ADD COLUMN description TEXT
        """)

    if "url" not in columns:
        cursor.execute("""
            ALTER TABLE contents
            ADD COLUMN url TEXT
        """)

    if "display_order" not in columns:
        cursor.execute("""
            ALTER TABLE contents
            ADD COLUMN display_order INTEGER
        """)

    cursor.execute("PRAGMA table_info(menus)")

    menu_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "display_order" not in menu_columns:
        cursor.execute("""
            ALTER TABLE menus
            ADD COLUMN display_order INTEGER
        """)

    cursor.execute("PRAGMA table_info(media_groups)")

    group_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "display_order" not in group_columns:
        cursor.execute("""
            ALTER TABLE media_groups
            ADD COLUMN display_order INTEGER
        """)

    # =========================
    # ترتيب القوائم القديمة
    # =========================

    cursor.execute("""
        SELECT id
        FROM menus
        WHERE display_order IS NULL
    """)

    menus_to_update = cursor.fetchall()

    for menu in menus_to_update:

        menu_id = menu["id"]

        position = 0

        # الفروع
        cursor.execute("""
            SELECT id
            FROM menus
            WHERE parent_id = ?
            ORDER BY sort_order, id
        """, (menu_id,))

        children = cursor.fetchall()

        for child in children:
            cursor.execute("""
                UPDATE menus
                SET display_order = ?
                WHERE id = ?
            """, (position, child["id"]))

            position += 1

        # المحتويات
        cursor.execute("""
            SELECT id
            FROM contents
            WHERE menu_id = ?
            ORDER BY sort_order, id
        """, (menu_id,))

        contents = cursor.fetchall()

        for content in contents:
            cursor.execute("""
                UPDATE contents
                SET display_order = ?
                WHERE id = ?
            """, (position, content["id"]))

            position += 1

        # مجموعات الوسائط
        cursor.execute("""
            SELECT id
            FROM media_groups
            WHERE menu_id = ?
            ORDER BY sort_order, id
        """, (menu_id,))

        groups = cursor.fetchall()

        for group in groups:
            cursor.execute("""
                UPDATE media_groups
                SET display_order = ?
                WHERE id = ?
            """, (position, group["id"]))

            position += 1

    # =========================
    # ترتيب القوائم الرئيسية
    # =========================

    cursor.execute("""
        SELECT id
        FROM menus
        WHERE parent_id IS NULL
        AND display_order IS NULL
        ORDER BY sort_order, id
    """)

    roots = cursor.fetchall()

    for position, root in enumerate(roots):

        cursor.execute("""
            UPDATE menus
            SET display_order = ?
            WHERE id = ?
        """, (position, root["id"]))

    connection.commit()

    connection.close()


# =========================
# ترتيب العنصر الجديد
# =========================

def next_display_order(menu_id):

    connection = get_connection()
    cursor = connection.cursor()

    values = []

    # الفروع
    cursor.execute("""
        SELECT COALESCE(
            MAX(display_order),
            -1
        ) AS value
        FROM menus
        WHERE parent_id = ?
    """, (menu_id,))

    values.append(
        cursor.fetchone()["value"]
    )

    # المحتوى
    cursor.execute("""
        SELECT COALESCE(
            MAX(display_order),
            -1
        ) AS value
        FROM contents
        WHERE menu_id = ?
    """, (menu_id,))

    values.append(
        cursor.fetchone()["value"]
    )

    # مجموعات الوسائط
    cursor.execute("""
        SELECT COALESCE(
            MAX(display_order),
            -1
        ) AS value
        FROM media_groups
        WHERE menu_id = ?
    """, (menu_id,))

    values.append(
        cursor.fetchone()["value"]
    )

    connection.close()

    return max(values) + 1


# =========================
# تسجيل المستخدم
# =========================

def register_user(user):

    connection = get_connection()

    connection.execute("""
        INSERT INTO users (
            user_id,
            first_name,
            username
        )
        VALUES (?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            first_name = excluded.first_name,
            username = excluded.username,
            last_seen = CURRENT_TIMESTAMP
    """, (
        user.id,
        user.first_name or "",
        user.username or ""
    ))

    connection.commit()

    connection.close()


# =========================
# التحقق من المشرف
# =========================

def is_admin(user_id):

    connection = get_connection()

    row = connection.execute("""
        SELECT 1
        FROM admins
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    connection.close()

    return row is not None


# =========================
# إضافة مشرف
# =========================

def add_admin(user_id):

    connection = get_connection()

    connection.execute("""
        INSERT OR IGNORE INTO admins (
            user_id
        )
        VALUES (?)
    """, (user_id,))

    connection.commit()

    connection.close()


# =========================
# حذف مشرف
# =========================

def remove_admin(user_id):

    connection = get_connection()

    connection.execute("""
        DELETE FROM admins
        WHERE user_id = ?
    """, (user_id,))

    connection.commit()

    connection.close()
