"""Background download manager with queue."""
import os
import time
import random
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import DOWNLOAD_DIR, MAX_CONCURRENT_DOWNLOADS, CHUNK_SIZE, REQUEST_TIMEOUT, USER_AGENTS
from core.database import db
from core.proxy_manager import proxy_manager

class DownloadManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS)
        self.active_downloads = {}
        self._lock = threading.Lock()
        self._callbacks = []

    def register_callback(self, callback):
        self._callbacks.append(callback)

    def _notify(self, manga_id, chapter_id, status, progress=0):
        for cb in self._callbacks:
            try:
                cb(manga_id, chapter_id, status, progress)
            except:
                pass

    def queue_chapter(self, manga_id, chapter_id, title, page_urls):
        db.add_download(manga_id, chapter_id, title)
        db.update_download_status(manga_id, chapter_id, 'queued', total_pages=len(page_urls))

        future = self.executor.submit(
            self._download_chapter,
            manga_id, chapter_id, title, page_urls
        )
        with self._lock:
            self.active_downloads[(manga_id, chapter_id)] = future

    def _download_chapter(self, manga_id, chapter_id, title, page_urls):
        chapter_dir = os.path.join(DOWNLOAD_DIR, manga_id, chapter_id)
        os.makedirs(chapter_dir, exist_ok=True)

        db.update_download_status(manga_id, chapter_id, 'downloading', total_pages=len(page_urls))
        self._notify(manga_id, chapter_id, 'downloading', 0)

        downloaded = 0
        errors = 0

        for i, url in enumerate(page_urls):
            if errors > 5:
                db.update_download_status(manga_id, chapter_id, 'failed')
                self._notify(manga_id, chapter_id, 'failed', 0)
                return

            ext = url.split('.')[-1].split('?')[0]
            if len(ext) > 5 or not ext:
                ext = 'jpg'
            filepath = os.path.join(chapter_dir, f"page_{i:03d}.{ext}")

            success = False
            for attempt in range(3):
                try:
                    headers = {
                        'User-Agent': random.choice(USER_AGENTS),
                        'Referer': 'https://mangadex.org/',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    }
                    proxies = proxy_manager.get_proxy_dict()

                    r = requests.get(
                        url, 
                        headers=headers,
                        proxies=proxies,
                        timeout=REQUEST_TIMEOUT,
                        stream=True
                    )

                    if r.status_code == 200:
                        with open(filepath, 'wb') as f:
                            for chunk in r.iter_content(CHUNK_SIZE):
                                if chunk:
                                    f.write(chunk)
                        downloaded += 1
                        success = True
                        break
                    elif r.status_code in (403, 503):
                        proxy_manager.mark_failed()
                        time.sleep(2 ** attempt)
                except Exception as e:
                    time.sleep(1)

            if not success:
                errors += 1

            progress = (i + 1) / len(page_urls) * 100
            db.update_download_status(manga_id, chapter_id, 'downloading', 
                                       progress=progress, total_pages=len(page_urls),
                                       downloaded_pages=downloaded)
            self._notify(manga_id, chapter_id, 'downloading', progress)

        if downloaded > 0:
            db.mark_chapter_downloaded(manga_id, chapter_id, chapter_dir)
            db.update_download_status(manga_id, chapter_id, 'completed', progress=100,
                                       total_pages=len(page_urls), downloaded_pages=downloaded)
            self._notify(manga_id, chapter_id, 'completed', 100)
        else:
            db.update_download_status(manga_id, chapter_id, 'failed')
            self._notify(manga_id, chapter_id, 'failed', 0)

    def get_queue(self):
        return db.get_download_queue()

    def cancel_download(self, manga_id, chapter_id):
        key = (manga_id, chapter_id)
        with self._lock:
            if key in self.active_downloads:
                future = self.active_downloads[key]
                # Note: ThreadPoolExecutor futures can't truly be cancelled mid-execution,
                # but we remove from tracking
                del self.active_downloads[key]
        db.update_download_status(manga_id, chapter_id, 'cancelled')
        self._notify(manga_id, chapter_id, 'cancelled', 0)

    def clear_completed(self):
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM download_queue WHERE status IN ('completed', 'cancelled', 'failed')")
        db.conn.commit()

# Global instance
download_manager = DownloadManager()
