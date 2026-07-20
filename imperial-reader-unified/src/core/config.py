"""Configuration and constants for Imperial Reader."""
import os
from kivy.utils import platform

IS_ANDROID = platform == 'android'
IS_DESKTOP = platform in ('linux', 'win', 'macosx')

# Paths
if IS_ANDROID:
    from android.storage import app_storage_path
    BASE_DIR = app_storage_path()
else:
    BASE_DIR = os.path.expanduser("~/.imperial_reader")

os.makedirs(BASE_DIR, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, "library.db")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

for d in [DOWNLOAD_DIR, CACHE_DIR]:
    os.makedirs(d, exist_ok=True)

# Theme Colors
COLORS = {
    'primary': '#C9A227',      # Gold
    'background': '#0A0A0A',    # Black
    'surface': '#1A1A1A',      # Dark gray
    'surface_light': '#2A2A2A',
    'text': '#FFFFFF',
    'text_secondary': '#AAAAAA',
    'accent': '#C9A227',
    'error': '#CF6679',
    'success': '#4CAF50',
    'warning': '#FFA726',
}

# Proxy Settings
PROXY_MODES = ['DIRECT', 'BUILTIN_ROTATING', 'CUSTOM']
BUILTIN_PROXIES = [
    "http://103.152.232.73:8080",
    "http://43.153.99.175:8080",
    "http://47.88.31.196:8080",
    "http://154.203.132.49:8090",
    "http://47.243.175.55:8080",
    "http://103.152.232.73:3128",
    "http://43.153.99.175:3128",
    "http://47.88.31.196:3128",
    "http://154.203.132.49:3128",
    "http://47.243.175.55:3128",
]

# Download Settings
MAX_CONCURRENT_DOWNLOADS = 3
CHUNK_SIZE = 8192
REQUEST_TIMEOUT = 30

# User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
]
