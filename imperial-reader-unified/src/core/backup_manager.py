"""Mihon/Tachiyomi compatible backup import/export.

Backup format (Mihon/Tachiyomi JSON):
{
    "version": 2,
    "manga": [...],
    "categories": [...],
    "extensions": [...]
}
"""
import json
import time
import os
from core.config import BASE_DIR
from core.database import db

class BackupManager:
    BACKUP_VERSION = 2

    def export_mihon_backup(self, path=None):
        """Export library as Mihon-compatible JSON backup."""
        if path is None:
            path = os.path.join(BASE_DIR, f"imperial_backup_{int(time.time())}.json")

        library = db.get_library()
        categories = self._get_categories()

        manga_list = []
        for item in library:
            chapters = db.get_chapters(item['manga_id'])
            manga_list.append({
                "source": item.get('source', 'unknown'),
                "url": f"/title/{item['manga_id']}",
                "title": item['title'],
                "artist": "",
                "author": item.get('author', ''),
                "description": item.get('description', ''),
                "genre": [],
                "status": self._map_status(item.get('status', '0')),
                "thumbnailUrl": item.get('cover_url', ''),
                "dateAdded": int(item.get('date_added', 0) * 1000),
                "viewer": 0,
                "chapters": [
                    {
                        "url": f"/chapter/{ch['chapter_id']}",
                        "name": ch['title'],
                        "read": bool(ch.get('is_read', 0)),
                        "bookmark": False,
                        "lastPageRead": ch.get('last_page_read', 0),
                        "dateFetch": 0,
                        "dateUpload": 0,
                        "chapterNumber": ch.get('number', 0),
                    }
                    for ch in chapters
                ],
                "categories": json.loads(item.get('categories', '[]')) if item.get('categories') else [],
                "history": [],
            })

        backup = {
            "version": self.BACKUP_VERSION,
            "manga": manga_list,
            "categories": categories,
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(backup, f, ensure_ascii=False, indent=2)

        return path

    def import_mihon_backup(self, path):
        """Import Mihon/Tachiyomi JSON backup."""
        if not os.path.exists(path):
            return False

        with open(path, 'r', encoding='utf-8') as f:
            backup = json.load(f)

        version = backup.get('version', 1)
        manga_list = backup.get('manga', [])

        for m in manga_list:
            # Extract manga ID from URL
            url = m.get('url', '')
            manga_id = url.split('/')[-1] if '/' in url else url

            db.add_to_library({
                'id': manga_id,
                'title': m.get('title', 'Unknown'),
                'cover_url': m.get('thumbnailUrl', ''),
                'author': m.get('author', ''),
                'description': m.get('description', ''),
                'status': str(m.get('status', 0)),
                'source': m.get('source', 'unknown'),
                'categories': m.get('categories', []),
            })

            # Import chapters
            chapters = []
            for ch in m.get('chapters', []):
                ch_url = ch.get('url', '')
                ch_id = ch_url.split('/')[-1] if '/' in ch_url else ch_url
                chapters.append({
                    'id': ch_id,
                    'title': ch.get('name', ''),
                    'number': ch.get('chapterNumber', 0),
                    'date_uploaded': '',
                })

            if chapters:
                db.save_chapters(manga_id, chapters)

        # Import categories
        for cat in backup.get('categories', []):
            if isinstance(cat, str):
                db.conn.cursor().execute(
                    'INSERT OR IGNORE INTO categories (name) VALUES (?)', (cat,)
                )
        db.conn.commit()

        return True

    def _get_categories(self):
        cursor = db.conn.cursor()
        cursor.execute('SELECT name FROM categories ORDER BY order_index')
        return [row[0] for row in cursor.fetchall()]

    def _map_status(self, status):
        status_map = {
            'Unknown': 0, 'Ongoing': 1, 'Completed': 2, 'Licensed': 3,
            'Publishing Finished': 4, 'Cancelled': 5, 'On Hiatus': 6,
        }
        return status_map.get(str(status), 0)

# Global instance
backup_manager = BackupManager()
