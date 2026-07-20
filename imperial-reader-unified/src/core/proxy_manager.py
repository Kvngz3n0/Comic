"""Proxy rotation and management."""
import random
import requests
import time
from core.config import PROXY_MODES, BUILTIN_PROXIES, USER_AGENTS
from core.database import db

class ProxyManager:
    def __init__(self):
        self.mode = db.get_setting('proxy_mode', 'DIRECT')
        self.custom_proxy = db.get_setting('custom_proxy', '')
        self.current_proxy = None
        self.failed_proxies = set()
        self._builtin_index = 0

    def get_proxy_dict(self):
        if self.mode == 'DIRECT':
            return {}

        if self.mode == 'CUSTOM' and self.custom_proxy:
            return {'http': self.custom_proxy, 'https': self.custom_proxy}

        if self.mode == 'BUILTIN_ROTATING':
            return self._get_rotating_proxy()

        return {}

    def _get_rotating_proxy(self):
        available = [p for p in BUILTIN_PROXIES if p not in self.failed_proxies]
        if not available:
            self.failed_proxies.clear()
            available = BUILTIN_PROXIES

        proxy = available[self._builtin_index % len(available)]
        self._builtin_index += 1
        self.current_proxy = proxy
        return {'http': proxy, 'https': proxy}

    def mark_failed(self, proxy=None):
        if proxy:
            self.failed_proxies.add(proxy)
        elif self.current_proxy:
            self.failed_proxies.add(self.current_proxy)

    def test_proxy(self, proxy_url=None):
        test_url = 'https://httpbin.org/ip'
        proxy = proxy_url or self.custom_proxy
        if not proxy:
            return False, "No proxy configured"

        try:
            start = time.time()
            r = requests.get(
                test_url, 
                proxies={'http': proxy, 'https': proxy},
                timeout=10,
                headers={'User-Agent': random.choice(USER_AGENTS)}
            )
            latency = time.time() - start
            if r.status_code == 200:
                return True, f"OK ({latency:.2f}s) - {r.json().get('origin', 'unknown')}"
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)

    def set_mode(self, mode):
        if mode in PROXY_MODES:
            self.mode = mode
            db.set_setting('proxy_mode', mode)

    def set_custom_proxy(self, proxy_url):
        self.custom_proxy = proxy_url
        db.set_setting('custom_proxy', proxy_url)

# Global instance
proxy_manager = ProxyManager()
