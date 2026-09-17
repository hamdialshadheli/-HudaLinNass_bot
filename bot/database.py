import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data") / "huda.db"


def get_connection():
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    # =====================================================
    # القوائم
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (parent_id)
            REFERENCES menus(id)
        )
        """
    )

    # =====================================================
    # المحتويات الفردية القديمة
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL,
            text_content TEXT,
            file_id TEXT,
            caption TEXT,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (menu_id)
            REFERENCES menus(id)
        )
        """
    )

    # =====================================================
    # التأكد من وجود description في قاعدة قديمة
    # =====================================================

    cursor.execute(
        "PRAGMA table_info(contents)"
    )

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "description" not in columns:

        cursor.execute(
            """
            ALTER TABLE contents
            ADD COLUMN description TEXT
            """
        )

    # =====================================================
    # مجموعات الملفات
    #
    # المجموعة = زر واحد داخل القائمة
    #
    # مثال:
    #
    # 🖼️ تفسير سورة البقرة
    #
    # وتحته:
    # صورة 1
    # صورة 2
    # صورة 3
    # ...
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS media_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            media_type TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (menu_id)
            REFERENCES menus(id)
        )
        """
    )

    # =====================================================
    # ملفات المجموعة
    # =====================================================

    cursor.execute(
        """
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
        """
    )

    connection.commit()
    connection.close()
