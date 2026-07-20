"""SQLite database for Library, Search History, and Downloads."""
import sqlite3
import json
import time
import os
from threading import Lock
from core.config import DB_PATH

class Database:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()

        # Library (saved manga)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manga_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                cover_url TEXT,
                author TEXT,
                description TEXT,
                status TEXT,
                source TEXT,
                categories TEXT,
                date_added REAL,
                last_read REAL,
                is_favorite INTEGER DEFAULT 0
            )
        """)

        # Chapters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manga_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                title TEXT,
                number REAL,
                date_uploaded TEXT,
                is_read INTEGER DEFAULT 0,
                is_downloaded INTEGER DEFAULT 0,
                download_path TEXT,
                last_page_read INTEGER DEFAULT 0,
                UNIQUE(manga_id, chapter_id)
            )
        """)

        # Search History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT UNIQUE NOT NULL,
                timestamp REAL NOT NULL
            )
        """)

        # Download Queue
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manga_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                title TEXT,
                status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0,
                total_pages INTEGER DEFAULT 0,
                downloaded_pages INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                timestamp REAL,
                UNIQUE(manga_id, chapter_id)
            )
        """)

        # Categories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                order_index INTEGER DEFAULT 0
            )
        """)

        # Settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        
        # Repositories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                name TEXT,
                json_data TEXT,
                date_added REAL,
                is_enabled INTEGER DEFAULT 1
            )
        """)
self.conn.commit()

    # Library operations
    def add_to_library(self, manga):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO library 
            (manga_id, title, cover_url, author, description, status, source, categories, date_added, last_read, is_favorite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            manga.get('id'), manga.get('title'), manga.get('cover_url'),
            manga.get('author'), manga.get('description'), manga.get('status'),
            manga.get('source'), json.dumps(manga.get('categories', [])),
            time.time(), manga.get('last_read', 0), 1
        ))
        self.conn.commit()

    def remove_from_library(self, manga_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM library WHERE manga_id = ?', (manga_id,))
        cursor.execute('DELETE FROM chapters WHERE manga_id = ?', (manga_id,))
        self.conn.commit()

    def get_library(self, category=None):
        cursor = self.conn.cursor()
        if category:
            cursor.execute('SELECT * FROM library WHERE categories LIKE ? ORDER BY date_added DESC', (f'%"{category}"%',))
        else:
            cursor.execute('SELECT * FROM library ORDER BY date_added DESC')
        return [dict(row) for row in cursor.fetchall()]

    def is_in_library(self, manga_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM library WHERE manga_id = ?', (manga_id,))
        return cursor.fetchone() is not None

    # Chapter operations
    def save_chapters(self, manga_id, chapters):
        cursor = self.conn.cursor()
        for ch in chapters:
            cursor.execute("""
                INSERT OR REPLACE INTO chapters 
                (manga_id, chapter_id, title, number, date_uploaded)
                VALUES (?, ?, ?, ?, ?)
            """, (manga_id, ch.get('id'), ch.get('title'), ch.get('number'), ch.get('date_uploaded')))
        self.conn.commit()

    def get_chapters(self, manga_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM chapters WHERE manga_id = ? ORDER BY number DESC', (manga_id,))
        return [dict(row) for row in cursor.fetchall()]

    def mark_chapter_read(self, manga_id, chapter_id, page=0):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE chapters SET is_read = 1, last_page_read = ? 
            WHERE manga_id = ? AND chapter_id = ?
        """, (page, manga_id, chapter_id))
        self.conn.commit()

    def mark_chapter_downloaded(self, manga_id, chapter_id, path):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE chapters SET is_downloaded = 1, download_path = ? 
            WHERE manga_id = ? AND chapter_id = ?
        """, (path, manga_id, chapter_id))
        self.conn.commit()

    # Search history
    def add_search_history(self, query):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO search_history (query, timestamp) 
            VALUES (?, ?)
        """, (query, time.time()))
        # Keep only last 50
        cursor.execute("""
            DELETE FROM search_history WHERE id NOT IN 
            (SELECT id FROM search_history ORDER BY timestamp DESC LIMIT 50)
        """)
        self.conn.commit()

    def get_search_history(self, limit=15):
        cursor = self.conn.cursor()
        cursor.execute('SELECT query FROM search_history ORDER BY timestamp DESC LIMIT ?', (limit,))
        return [row[0] for row in cursor.fetchall()]

    def clear_search_history(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM search_history')
        self.conn.commit()

    # Download queue
    def add_download(self, manga_id, chapter_id, title):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO download_queue 
            (manga_id, chapter_id, title, status, timestamp)
            VALUES (?, ?, ?, 'pending', ?)
        """, (manga_id, chapter_id, title, time.time()))
        self.conn.commit()

    def update_download_status(self, manga_id, chapter_id, status, progress=0, total_pages=0, downloaded_pages=0):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE download_queue SET status = ?, progress = ?, total_pages = ?, downloaded_pages = ?
            WHERE manga_id = ? AND chapter_id = ?
        """, (status, progress, total_pages, downloaded_pages, manga_id, chapter_id))
        self.conn.commit()

    def get_download_queue(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM download_queue ORDER BY timestamp DESC')
        return [dict(row) for row in cursor.fetchall()]

    def remove_download(self, manga_id, chapter_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM download_queue WHERE manga_id = ? AND chapter_id = ?', (manga_id, chapter_id))
        self.conn.commit()

    # Settings
    def set_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
        self.conn.commit()

    def get_setting(self, key, default=None):
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row[0] if row else default


    # Repo operations
    def add_repo(self, url, name, json_data):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO repos (url, name, json_data, date_added, is_enabled)
            VALUES (?, ?, ?, ?, 1)
        """, (url, name, json_data, time.time()))
        self.conn.commit()

    def remove_repo(self, url):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM repos WHERE url = ?', (url,))
        self.conn.commit()

    def get_repos(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM repos WHERE is_enabled = 1 ORDER BY date_added DESC')
        return [dict(row) for row in cursor.fetchall()]

    def toggle_repo(self, url, enabled):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE repos SET is_enabled = ? WHERE url = ?', (1 if enabled else 0, url))
        self.conn.commit()

# Global instance
db = Database()
