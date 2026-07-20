"""Settings screen with proxy, cloudflare, repo, and backup options."""
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.metrics import dp

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.selectioncontrol import MDSwitch

from core.config import COLORS, PROXY_MODES, BUILTIN_PROXIES
from core.database import db
from core.proxy_manager import proxy_manager
from core.extension_manager import extension_manager


class RepoItem(MDCard):
    def __init__(self, repo, on_remove, **kwargs):
        super().__init__(**kwargs)
        self.repo = repo
        self.on_remove = on_remove
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(60)
        self.md_bg_color = COLORS['surface']
        self.radius = [dp(4),]
        self.padding = dp(8)

        info = BoxLayout(orientation='vertical')
        info.add_widget(MDLabel(
            text=repo.get('name', 'Unknown Repo'),
            theme_text_color='Custom', text_color=COLORS['text'],
            font_style='Body1', size_hint_y=0.6,
        ))
        info.add_widget(MDLabel(
            text=repo.get('url', '')[:50] + '...',
            theme_text_color='Custom', text_color=COLORS['text_secondary'],
            font_style='Caption', size_hint_y=0.4,
        ))
        self.add_widget(info)

        self.add_widget(MDIconButton(
            icon='delete', theme_text_color='Custom',
            text_color=COLORS['error'], on_release=self._remove,
        ))

    def _remove(self, instance):
        self.on_remove(self.repo.get('url'))


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = COLORS['background']
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')

        scroll = ScrollView()
        content = GridLayout(cols=1, spacing=dp(12), padding=dp(16), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        # ===== PROXY SECTION =====
        content.add_widget(self._section_title("Proxy Settings"))

        proxy_card = MDCard(orientation='vertical', size_hint_y=None, height=dp(250),
                           md_bg_color=COLORS['surface'], radius=[dp(8),], padding=dp(12))

        proxy_card.add_widget(MDLabel(text="Proxy Mode", theme_text_color='Custom',
                                      text_color=COLORS['text_secondary'], font_style='Caption'))

        self.proxy_mode_btn = MDRaisedButton(
            text=db.get_setting('proxy_mode', 'DIRECT'),
            md_bg_color=COLORS['surface_light'], text_color=COLORS['primary'],
            on_release=self.show_proxy_modes,
        )
        proxy_card.add_widget(self.proxy_mode_btn)

        proxy_card.add_widget(MDLabel(text="Custom Proxy (http://ip:port)",
                                      theme_text_color='Custom', text_color=COLORS['text_secondary'],
                                      font_style='Caption'))
        self.proxy_input = MDTextField(
            text=db.get_setting('custom_proxy', ''),
            hint_text="http://proxy:8080",
            text_color_normal=COLORS['text_secondary'],
            text_color_focus=COLORS['primary'],
            line_color_normal=COLORS['surface_light'],
            line_color_focus=COLORS['primary'],
        )
        proxy_card.add_widget(self.proxy_input)

        test_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        test_box.add_widget(MDRaisedButton(
            text='Test Proxy', md_bg_color=COLORS['primary'],
            text_color=COLORS['background'], on_release=self.test_proxy,
        ))
        test_box.add_widget(MDFlatButton(
            text='Save', text_color=COLORS['primary'],
            on_release=self.save_proxy,
        ))
        proxy_card.add_widget(test_box)

        self.proxy_status = MDLabel(
            text="", theme_text_color='Custom',
            text_color=COLORS['text_secondary'], font_style='Caption',
        )
        proxy_card.add_widget(self.proxy_status)
        content.add_widget(proxy_card)

        # ===== CLOUDFLARE SECTION =====
        content.add_widget(self._section_title("Cloudflare Bypass"))

        cf_card = MDCard(orientation='vertical', size_hint_y=None, height=dp(120),
                        md_bg_color=COLORS['surface'], radius=[dp(8),], padding=dp(12))

        cf_row = BoxLayout(size_hint_y=None, height=dp(40))
        cf_row.add_widget(MDLabel(
            text="Enable WebView Bypass",
            theme_text_color='Custom', text_color=COLORS['text'],
        ))
        self.cf_switch = MDSwitch(
            active=db.get_setting('cf_bypass', 'true').lower() == 'true',
            thumb_color_active=COLORS['primary'],
            track_color_active=COLORS['primary'],
        )
        self.cf_switch.bind(active=self.on_cf_toggle)
        cf_row.add_widget(self.cf_switch)
        cf_card.add_widget(cf_row)

        cf_card.add_widget(MDLabel(
            text="Uses Mihon/Tachiyomi method: WebView solves JS challenge, extracts cf_clearance cookie.",
            theme_text_color='Custom', text_color=COLORS['text_secondary'],
            font_style='Caption',
        ))
        content.add_widget(cf_card)

        # ===== REPO MANAGEMENT SECTION =====
        content.add_widget(self._section_title("Extension Repos"))

        repo_card = MDCard(orientation='vertical', size_hint_y=None, height=dp(320),
                          md_bg_color=COLORS['surface'], radius=[dp(8),], padding=dp(12))

        # Popular repos quick-add
        popular_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        popular_box.add_widget(MDLabel(
            text="Popular:", theme_text_color='Custom',
            text_color=COLORS['text_secondary'], font_style='Caption',
            size_hint_x=None, width=dp(60),
        ))
        popular_box.add_widget(MDFlatButton(
            text='Keiyoushi', text_color=COLORS['primary'],
            on_release=lambda x: self.add_popular_repo('keiyoushi'),
        ))
        popular_box.add_widget(MDFlatButton(
            text='Mihon Official', text_color=COLORS['primary'],
            on_release=lambda x: self.add_popular_repo('mihon'),
        ))
        repo_card.add_widget(popular_box)

        # Add repo URL input
        repo_card.add_widget(MDLabel(
            text="Add Custom Repo URL (.json)",
            theme_text_color='Custom', text_color=COLORS['text_secondary'],
            font_style='Caption',
        ))

        input_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        self.repo_input = MDTextField(
            hint_text="https://raw.githubusercontent.com/.../repo.json",
            text_color_normal=COLORS['text_secondary'],
            text_color_focus=COLORS['primary'],
            line_color_normal=COLORS['surface_light'],
            line_color_focus=COLORS['primary'],
        )
        input_box.add_widget(self.repo_input)
        input_box.add_widget(MDRaisedButton(
            text='Add', md_bg_color=COLORS['primary'],
            text_color=COLORS['background'], on_release=self.add_repo,
            size_hint_x=None, width=dp(80),
        ))
        repo_card.add_widget(input_box)

        self.repo_status = MDLabel(
            text="", theme_text_color='Custom',
            text_color=COLORS['text_secondary'], font_style='Caption',
        )
        repo_card.add_widget(self.repo_status)

        # Repo list header
        repo_card.add_widget(BoxLayout(size_hint_y=None, height=dp(8)))
        repo_card.add_widget(MDLabel(
            text="Added Repositories:",
            theme_text_color='Custom', text_color=COLORS['primary'],
            font_style='Subtitle1', size_hint_y=None, height=dp(30),
        ))

        # Repo list container
        self.repo_list = GridLayout(
            cols=1, spacing=dp(4), size_hint_y=None,
        )
        self.repo_list.bind(minimum_height=self.repo_list.setter('height'))
        repo_card.add_widget(self.repo_list)

        # Refresh button
        repo_card.add_widget(MDFlatButton(
            text='Refresh All Repos', text_color=COLORS['primary'],
            on_release=self.refresh_repos,
        ))

        content.add_widget(repo_card)

        # ===== BACKUP SECTION =====
        content.add_widget(self._section_title("Backup & Restore"))

        backup_card = MDCard(orientation='vertical', size_hint_y=None, height=dp(150),
                            md_bg_color=COLORS['surface'], radius=[dp(8),], padding=dp(12))

        backup_card.add_widget(MDLabel(
            text="Mihon/Tachiyomi Compatible",
            theme_text_color='Custom', text_color=COLORS['primary'],
            font_style='Subtitle1',
        ))

        backup_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        backup_row.add_widget(MDRaisedButton(
            text='Export Backup', md_bg_color=COLORS['primary'],
            text_color=COLORS['background'], on_release=self.export_backup,
        ))
        backup_row.add_widget(MDRaisedButton(
            text='Import Backup', md_bg_color=COLORS['surface_light'],
            text_color=COLORS['primary'], on_release=self.import_backup,
        ))
        backup_card.add_widget(backup_row)

        backup_card.add_widget(MDLabel(
            text="Exports/imports .json backups compatible with Mihon/Tachiyomi.",
            theme_text_color='Custom', text_color=COLORS['text_secondary'],
            font_style='Caption',
        ))
        content.add_widget(backup_card)

        # About
        content.add_widget(self._section_title("About"))
        content.add_widget(MDLabel(
            text="Imperial Reader v1.0\nBlack & Gold Theme\nBuilt with KivyMD",
            halign='center', theme_text_color='Custom',
            text_color=COLORS['text_secondary'], font_style='Caption',
        ))

        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)

        # Load repos on init
        Clock.schedule_once(lambda dt: self.load_repos(), 0.3)

    def _section_title(self, text):
        return MDLabel(
            text=text, theme_text_color='Custom',
            text_color=COLORS['primary'], font_style='H6',
            size_hint_y=None, height=dp(30),
        )

    # Proxy methods
    def show_proxy_modes(self, instance):
        from kivymd.uix.menu import MDDropdownMenu
        menu_items = [
            {"text": mode, "viewclass": "OneLineListItem",
             "on_release": lambda x=mode: self.set_proxy_mode(x)}
            for mode in PROXY_MODES
        ]
        menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        menu.open()

    def set_proxy_mode(self, mode):
        proxy_manager.set_mode(mode)
        self.proxy_mode_btn.text = mode

    def test_proxy(self, instance):
        proxy = self.proxy_input.text.strip()
        success, msg = proxy_manager.test_proxy(proxy)
        self.proxy_status.text = f"Test: {msg}"
        self.proxy_status.text_color = COLORS['success'] if success else COLORS['error']

    def save_proxy(self, instance):
        proxy_manager.set_custom_proxy(self.proxy_input.text.strip())
        self.proxy_status.text = "Proxy saved."
        self.proxy_status.text_color = COLORS['success']

    # Cloudflare
    def on_cf_toggle(self, instance, value):
        db.set_setting('cf_bypass', str(value).lower())

    # Repo methods
    def load_repos(self):
        self.repo_list.clear_widgets()
        repos = db.get_repos()

        if not repos:
            self.repo_list.add_widget(MDLabel(
                text="No custom repos added yet.",
                theme_text_color='Custom', text_color=COLORS['text_secondary'],
                font_style='Caption', size_hint_y=None, height=dp(30),
            ))
            return

        for repo in repos:
            self.repo_list.add_widget(RepoItem(repo, self.remove_repo))

    def add_repo(self, instance):
        url = self.repo_input.text.strip()
        if not url:
            self.repo_status.text = "Please enter a URL"
            self.repo_status.text_color = COLORS['error']
            return

        self.repo_status.text = "Fetching repo..."
        self.repo_status.text_color = COLORS['primary']

        def _do_add(dt):
            success, msg = extension_manager.add_repo_url(url)
            self.repo_status.text = msg
            self.repo_status.text_color = COLORS['success'] if success else COLORS['error']
            if success:
                self.repo_input.text = ""
                self.load_repos()
                # Refresh browse screen sources
                from kivymd.app import MDApp
                app = MDApp.get_running_app()
                if hasattr(app, 'browse_screen'):
                    app.browse_screen.refresh_sources()

        Clock.schedule_once(_do_add, 0.1)

    def add_popular_repo(self, repo_name):
        urls = {
            'keiyoushi': 'https://raw.githubusercontent.com/keiyoushi/extensions/repo/index.min.json',
            'mihon': 'https://raw.githubusercontent.com/tachiyomiorg/extensions/repo/index.min.json',
        }
        url = urls.get(repo_name, '')
        if url:
            self.repo_input.text = url
            self.add_repo(None)

    def remove_repo(self, url):
        extension_manager.remove_repo(url)
        self.load_repos()
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        if hasattr(app, 'browse_screen'):
            app.browse_screen.refresh_sources()

    def refresh_repos(self, instance):
        self.repo_status.text = "Refreshing all repos..."
        self.repo_status.text_color = COLORS['primary']

        def _refresh(dt):
            extension_manager.refresh_repos()
            self.load_repos()
            self.repo_status.text = "All repos refreshed."
            self.repo_status.text_color = COLORS['success']

        Clock.schedule_once(_refresh, 0.1)

    # Backup methods
    def export_backup(self, instance):
        from core.backup_manager import backup_manager
        path = backup_manager.export_mihon_backup()
        self._show_dialog("Backup Exported", f"Saved to:\n{path}")

    def import_backup(self, instance):
        from core.backup_manager import backup_manager
        path = db.get_setting('last_backup_path', '')
        if path:
            backup_manager.import_mihon_backup(path)
            self._show_dialog("Backup Imported", "Library restored from backup.")
        else:
            self._show_dialog("Import", "Place .json backup in app folder and set path in settings.")

    def _show_dialog(self, title, text):
        dialog = MDDialog(
            title=title, text=text,
            buttons=[MDFlatButton(text="OK", text_color=COLORS['primary'],
                                 on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()
