"""Extension system for manga sources with dynamic repo support."""
import os
import json
import requests
from core.config import CACHE_DIR, USER_AGENTS, REQUEST_TIMEOUT
from core.proxy_manager import proxy_manager
from core.database import db

class ExtensionManager:
    def __init__(self):
        self.extensions = {}
        self._load_builtin_extensions()
        self._load_custom_repos()

    def _load_builtin_extensions(self):
        self.extensions['mangadex'] = {
            'id': 'mangadex',
            'name': 'MangaDex',
            'lang': 'en',
            'base_url': 'https://api.mangadex.org',
            'icon': '📚',
            'repo': 'Built-in',
        }
        self.extensions['demo'] = {
            'id': 'demo',
            'name': 'Demo Source',
            'lang': 'en',
            'base_url': '',
            'icon': '🧪',
            'repo': 'Built-in',
        }

    def _load_custom_repos(self):
        """Load all saved repo URLs from database."""
        repos = db.get_repos()
        for repo in repos:
            try:
                data = json.loads(repo.get('json_data', '{}'))
                self._parse_repo_json(data, repo.get('name', 'Custom'))
            except:
                pass

    def add_repo_url(self, url):
        """Fetch and add a repo from URL. Returns (success, message)."""
        try:
            headers = {'User-Agent': USER_AGENTS[0], 'Accept': 'application/json'}
            proxies = proxy_manager.get_proxy_dict()
            r = requests.get(url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT)

            if r.status_code != 200:
                return False, f"HTTP {r.status_code}"

            data = r.json()

            # Validate repo format
            if 'extensions' not in data and 'sources' not in data:
                return False, "Invalid repo format (needs 'extensions' or 'sources' key)"

            repo_name = data.get('name', 'Custom Repo')

            # Save to DB
            db.add_repo(url, repo_name, r.text)

            # Parse and load
            self._parse_repo_json(data, repo_name)

            count = len(data.get('extensions', data.get('sources', [])))
            return True, f"Added {count} extensions from {repo_name}"

        except requests.exceptions.ConnectionError:
            return False, "Connection failed — check proxy/internet"
        except json.JSONDecodeError:
            return False, "Invalid JSON — not a valid repo file"
        except Exception as e:
            return False, str(e)

    def _parse_repo_json(self, data, repo_name):
        """Parse repo.json format (Mihon/Tachiyomi compatible)."""
        extensions = data.get('extensions', data.get('sources', []))

        for ext in extensions:
            ext_id = ext.get('pkg', ext.get('id', ext.get('name', '').lower().replace(' ', '_')))
            if not ext_id:
                continue

            # Make unique ID
            unique_id = f"{repo_name.lower().replace(' ', '_')}_{ext_id.split('.')[-1]}"

            self.extensions[unique_id] = {
                'id': unique_id,
                'name': ext.get('name', 'Unknown'),
                'lang': ext.get('lang', 'en'),
                'pkg': ext_id,
                'apk': ext.get('apk', ''),
                'version': ext.get('version', '1.0'),
                'nsfw': ext.get('nsfw', 0),
                'icon': self._get_icon_for_source(ext.get('name', '')),
                'repo': repo_name,
                'raw': ext,
            }

    def _get_icon_for_source(self, name):
        icons = {
            'mangadex': '📚', 'mangakakalot': '📖', 'manganato': '📕',
            'webtoon': '🌐', 'webtoons': '🌐', 'comick': '💨',
            'mangafire': '🔥', 'asura': '⚔️', 'asurascans': '⚔️',
            'reaper': '💀', 'reaperscans': '💀', 'flame': '🔥',
            'flamescans': '🔥', 'luminous': '✨', 'luminousscans': '✨',
            'immortal': '👑', 'immortalupdates': '👑',
        }
        name_lower = name.lower().replace(' ', '')
        for key, icon in icons.items():
            if key in name_lower:
                return icon
        return '📄'

    def get_extensions(self):
        return list(self.extensions.values())

    def remove_repo(self, url):
        db.remove_repo(url)
        self._reload_all()

    def _reload_all(self):
        self.extensions.clear()
        self._load_builtin_extensions()
        self._load_custom_repos()

    def refresh_repos(self):
        """Re-fetch all enabled repos to update extension lists."""
        repos = db.get_repos()
        for repo in repos:
            try:
                url = repo['url']
                headers = {'User-Agent': USER_AGENTS[0]}
                proxies = proxy_manager.get_proxy_dict()
                r = requests.get(url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT)
                if r.status_code == 200:
                    db.add_repo(url, repo.get('name', 'Custom'), r.text)
            except:
                pass
        self._reload_all()

    def search(self, source_id, query):
        if source_id == 'demo':
            return self._demo_search(query)
        elif source_id == 'mangadex':
            return self._mangadex_search(query)
        elif source_id in self.extensions:
            # For custom sources, try to use their base URL if available
            ext = self.extensions[source_id]
            raw = ext.get('raw', {})
            base_url = raw.get('baseUrl', raw.get('base_url', ''))
            if base_url:
                return self._generic_search(base_url, query)
        return []

    def _generic_search(self, base_url, query):
        """Generic search for custom sources (placeholder)."""
        return []

    def _demo_search(self, query):
        return [
            {
                'id': f'demo_{i}',
                'title': f'{query} - Demo Chapter {i+1}',
                'cover_url': '',
                'author': 'Demo Author',
                'description': 'This is demo data for testing.',
                'status': 'Ongoing',
                'source': 'demo',
                'chapters': [
                    {'id': f'ch_{i}_1', 'title': f'Chapter {i+1}.1', 'number': i+1.1},
                    {'id': f'ch_{i}_2', 'title': f'Chapter {i+1}.2', 'number': i+1.2},
                ]
            }
            for i in range(5)
        ]

    def _mangadex_search(self, query):
        try:
            headers = {'User-Agent': USER_AGENTS[0]}
            proxies = proxy_manager.get_proxy_dict()
            url = f"https://api.mangadex.org/manga?title={query}&limit=20&includes[]=cover_art"
            r = requests.get(url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT)
            data = r.json()

            results = []
            for item in data.get('data', []):
                attrs = item.get('attributes', {})
                cover_rel = None
                for rel in item.get('relationships', []):
                    if rel.get('type') == 'cover_art':
                        cover_rel = rel
                        break

                cover_url = ''
                if cover_rel:
                    cover_id = cover_rel.get('attributes', {}).get('fileName', '')
                    if cover_id:
                        cover_url = f"https://uploads.mangadex.org/covers/{item['id']}/{cover_id}"

                title = attrs.get('title', {}).get('en', 'Unknown')
                if not title:
                    title = list(attrs.get('title', {}).values())[0] if attrs.get('title') else 'Unknown'

                results.append({
                    'id': item['id'],
                    'title': title,
                    'cover_url': cover_url,
                    'author': ', '.join([a.get('attributes', {}).get('name', '') 
                                        for a in item.get('relationships', []) 
                                        if a.get('type') == 'author']),
                    'description': attrs.get('description', {}).get('en', ''),
                    'status': attrs.get('status', 'Unknown'),
                    'source': 'mangadex',
                })
            return results
        except Exception as e:
            print(f"MangaDex search error: {e}")
            return []

    def get_chapters(self, source_id, manga_id):
        if source_id == 'demo':
            return [
                {'id': f'ch_{i}', 'title': f'Chapter {i+1}', 'number': float(i+1), 'date_uploaded': '2024-01-01'}
                for i in range(20)
            ]
        elif source_id == 'mangadex':
            try:
                headers = {'User-Agent': USER_AGENTS[0]}
                proxies = proxy_manager.get_proxy_dict()
                url = f"https://api.mangadex.org/manga/{manga_id}/feed?limit=100&order[chapter]=desc&translatedLanguage[]=en"
                r = requests.get(url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT)
                data = r.json()

                chapters = []
                for item in data.get('data', []):
                    attrs = item.get('attributes', {})
                    chapters.append({
                        'id': item['id'],
                        'title': attrs.get('title', f"Chapter {attrs.get('chapter', '?')}"),
                        'number': float(attrs.get('chapter', 0) or 0),
                        'date_uploaded': attrs.get('createdAt', ''),
                    })
                return chapters
            except Exception as e:
                print(f"MangaDex chapters error: {e}")
                return []
        return []

    def get_pages(self, source_id, chapter_id):
        if source_id == 'demo':
            return [f"https://via.placeholder.com/800x1200/1A1A1A/C9A227?text=Demo+Page+{i+1}" for i in range(10)]
        elif source_id == 'mangadex':
            try:
                headers = {'User-Agent': USER_AGENTS[0]}
                proxies = proxy_manager.get_proxy_dict()
                url = f"https://api.mangadex.org/at-home/server/{chapter_id}"
                r = requests.get(url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT)
                data = r.json()

                base_url = data.get('baseUrl', '')
                chapter = data.get('chapter', {})
                hash_val = chapter.get('hash', '')
                pages = chapter.get('data', [])

                return [f"{base_url}/data/{hash_val}/{page}" for page in pages]
            except Exception as e:
                print(f"MangaDex pages error: {e}")
                return []
        return []

# Global instance
extension_manager = ExtensionManager()
