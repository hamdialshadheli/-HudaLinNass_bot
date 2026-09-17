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

    # ==========================================
    # القوائم
    # ==========================================

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

    # ==========================================
    # المحتوى
    # ==========================================

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
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (menu_id)
            REFERENCES menus(id)
        )
        """
    )

    connection.commit()

    connection.close()
