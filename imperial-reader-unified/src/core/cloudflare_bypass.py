"""Cloudflare bypass using Mihon/Tachiyomi WebView method.

Strategy (from actual Mihon source):
1. Detect CF challenge: 503/403 + cf-ray header + challenge body
2. Launch WebView with real browser UA
3. Wait for __cf_chl parameter to disappear from URL
4. Extract cf_clearance cookies
5. Retry original request with new cookies
"""
import re
import time
import random
import requests
from core.config import USER_AGENTS, REQUEST_TIMEOUT
from core.database import db

class CloudflareBypass:
    CF_INDICATORS = [
        b'cf-browser-verification',
        b'cf-challenge-running',
        b'__cf_chl_jschl_tk__',
        b'cf_chl_rc_ni',
        b'challenge-platform',
        b'challenge-form',
    ]

    def __init__(self):
        self.session = requests.Session()
        self.cf_cookies = {}

    def is_cloudflare_challenge(self, response):
        """Check if response is a Cloudflare challenge page."""
        if response.status_code not in (403, 503):
            return False

        # Check for cf-ray header
        if 'cf-ray' not in response.headers:
            return False

        # Check body for challenge indicators
        body = response.content
        for indicator in self.CF_INDICATORS:
            if indicator in body:
                return True

        # Check for challenge script pattern
        if b'jschl_vc' in body or b'jschl_answer' in body:
            return True

        return False

    def solve_with_webview(self, url, headers=None, proxies=None):
        """Solve CF challenge using WebView (Android) or selenium-like approach.

        On Android: Uses android.webkit.WebView
        On Desktop: Uses requests with cookie persistence + manual delay
        """
        from core.config import IS_ANDROID

        if IS_ANDROID:
            return self._solve_android_webview(url)
        else:
            return self._solve_desktop(url, headers, proxies)

    def _solve_android_webview(self, url):
        """Android WebView approach - launches browser to solve JS challenge."""
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            CookieManager = autoclass('android.webkit.CookieManager')

            activity = PythonActivity.mActivity
            webview = WebView(activity)

            # Set real browser UA
            settings = webview.getSettings()
            settings.setUserAgentString(USER_AGENTS[0])
            settings.setJavaScriptEnabled(True)

            # Load challenge URL
            webview.loadUrl(url)

            # Wait for challenge to complete (URL no longer contains __cf_chl)
            max_wait = 30
            start = time.time()
            while time.time() - start < max_wait:
                current_url = webview.getUrl()
                if '__cf_chl' not in current_url:
                    break
                time.sleep(1)

            # Extract cookies
            cookie_manager = CookieManager.getInstance()
            cookie_str = cookie_manager.getCookie(url)

            if cookie_str:
                cookies = {}
                for cookie in cookie_str.split(';'):
                    if '=' in cookie:
                        k, v = cookie.strip().split('=', 1)
                        cookies[k] = v

                # Save cf_clearance
                if 'cf_clearance' in cookies:
                    db.set_setting('cf_clearance', cookies['cf_clearance'])
                    self.cf_cookies = cookies
                    return cookies

            return None
        except Exception as e:
            print(f"Android WebView CF bypass error: {e}")
            return None

    def _solve_desktop(self, url, headers=None, proxies=None):
        """Desktop fallback: try with delays and cookie rotation."""
        # Try with stored cf_clearance first
        stored_clearance = db.get_setting('cf_clearance', '')
        if stored_clearance:
            cookies = {'cf_clearance': stored_clearance}
            try:
                r = self.session.get(
                    url, headers=headers, proxies=proxies,
                    cookies=cookies, timeout=REQUEST_TIMEOUT
                )
                if r.status_code == 200:
                    return cookies
            except:
                pass

        # Try with different UAs and delays
        for attempt in range(5):
            try:
                test_headers = (headers or {}).copy()
                test_headers['User-Agent'] = random.choice(USER_AGENTS)
                test_headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                test_headers['Accept-Language'] = 'en-US,en;q=0.5'
                test_headers['Accept-Encoding'] = 'gzip, deflate'
                test_headers['DNT'] = '1'
                test_headers['Connection'] = 'keep-alive'

                r = self.session.get(
                    url, headers=test_headers, proxies=proxies,
                    timeout=REQUEST_TIMEOUT
                )

                if r.status_code == 200:
                    # Extract any new cookies
                    if 'cf_clearance' in self.session.cookies:
                        db.set_setting('cf_clearance', self.session.cookies['cf_clearance'])
                    return dict(self.session.cookies)

                # If still challenged, wait longer
                time.sleep(5 + attempt * 3)
            except Exception as e:
                time.sleep(2)

        return None

    def request(self, url, headers=None, proxies=None, **kwargs):
        """Make a request with automatic Cloudflare bypass."""
        # First attempt
        r = self.session.get(url, headers=headers, proxies=proxies, **kwargs)

        if not self.is_cloudflare_challenge(r):
            return r

        # CF challenge detected - try to bypass
        print(f"Cloudflare challenge detected for {url}")
        cookies = self.solve_with_webview(url, headers, proxies)

        if cookies:
            # Retry with bypass cookies
            r = self.session.get(url, headers=headers, proxies=proxies, cookies=cookies, **kwargs)

        return r

# Global instance
cf_bypass = CloudflareBypass()
