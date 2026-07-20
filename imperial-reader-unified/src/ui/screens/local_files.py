"""Local Files screen for CBZ and downloaded content."""
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.metrics import dp

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard

from core.config import COLORS, BASE_DIR, DOWNLOAD_DIR
from core.cbz_manager import CBZManager


class CBZCard(MDCard):
    def __init__(self, book, **kwargs):
        super().__init__(**kwargs)
        self.book = book
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(100)
        self.md_bg_color = COLORS['surface']
        self.radius = [dp(8),]
        self.padding = dp(8)

        info = BoxLayout(orientation='vertical')
        info.add_widget(MDLabel(
            text=book.get('title', 'Unknown'),
            theme_text_color='Custom', text_color=COLORS['text'],
            font_style='Subtitle1', size_hint_y=0.4,
        ))
        info.add_widget(MDLabel(
            text=book.get('author', 'Local File'),
            theme_text_color='Custom', text_color=COLORS['text_secondary'],
            font_style='Caption', size_hint_y=0.3,
        ))
        info.add_widget(MDLabel(
            text=f"{book.get('pages', 0)} pages",
            theme_text_color='Custom', text_color=COLORS['primary'],
            font_style='Overline', size_hint_y=0.3,
        ))
        self.add_widget(info)

        self.add_widget(MDIconButton(
            icon='book-open-variant', theme_text_color='Custom',
            text_color=COLORS['primary'], on_release=self.open_cbz,
        ))

    def open_cbz(self, instance):
        pages = CBZManager.read_cbz(self.book['path'])
        if pages:
            # Convert to data URLs for reader
            import base64
            page_urls = []
            for p in pages:
                ext = p['name'].split('.')[-1].lower()
                mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'webp': 'webp', 'gif': 'gif'}.get(ext, 'jpeg')
                b64 = base64.b64encode(p['data']).decode()
                page_urls.append(f"data:image/{mime};base64,{b64}")

            app = self.get_root_window().children[0].children[0]
            app.switch_to_reader(self.book['id'], 'local', page_urls, self.book['title'])


class LocalFilesScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = COLORS['background']
        self._build_ui()
        Clock.schedule_once(lambda dt: self.scan_files(), 0.3)

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')

        header = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(8))
        header.add_widget(MDLabel(
            text='Local Files', theme_text_color='Custom',
            text_color=COLORS['primary'], font_style='H6',
        ))
        header.add_widget(MDRaisedButton(
            text='Scan Folder', md_bg_color=COLORS['surface_light'],
            text_color=COLORS['primary'], on_release=self.scan_files,
        ))
        layout.add_widget(header)

        scroll = ScrollView()
        self.list_layout = GridLayout(
            cols=1, spacing=dp(8), padding=dp(8), size_hint_y=None,
        )
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def scan_files(self, instance=None):
        self.list_layout.clear_widgets()

        # Scan download dir and base dir for CBZ
        cbz_files = []
        cbz_files.extend(CBZManager.scan_cbz_directory(DOWNLOAD_DIR))
        cbz_files.extend(CBZManager.scan_cbz_directory(BASE_DIR))

        if not cbz_files:
            self.list_layout.add_widget(MDLabel(
                text="No CBZ files found.\nDownload chapters or add .cbz files.",
                halign='center', theme_text_color='Custom',
                text_color=COLORS['text_secondary'], size_hint_y=None, height=dp(100),
            ))
            return

        for book in cbz_files:
            self.list_layout.add_widget(CBZCard(book))
