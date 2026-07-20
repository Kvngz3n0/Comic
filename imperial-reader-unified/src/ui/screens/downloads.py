"""Downloads screen with queue management."""
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.metrics import dp

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.progressbar import MDProgressBar

from core.config import COLORS
from core.downloader import download_manager


class DownloadItem(MDCard):
    def __init__(self, item, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(80)
        self.md_bg_color = COLORS['surface']
        self.radius = [dp(4),]
        self.padding = dp(8)

        header = BoxLayout(size_hint_y=None, height=dp(30))
        header.add_widget(MDLabel(
            text=item.get('title', 'Unknown')[:30],
            theme_text_color='Custom', text_color=COLORS['text'], font_style='Body1',
        ))
        status_colors = {
            'pending': COLORS['text_secondary'], 'queued': COLORS['warning'],
            'downloading': COLORS['primary'], 'completed': COLORS['success'],
            'failed': COLORS['error'], 'cancelled': COLORS['error'],
        }
        status = item.get('status', 'pending')
        header.add_widget(MDLabel(
            text=status.upper(), theme_text_color='Custom',
            text_color=status_colors.get(status, COLORS['text_secondary']),
            font_style='Overline', halign='right', size_hint_x=None, width=dp(80),
        ))
        self.add_widget(header)

        self.progress_bar = MDProgressBar(
            value=item.get('progress', 0),
            color=COLORS['primary'], back_color=COLORS['surface_light'],
        )
        self.add_widget(self.progress_bar)

        info = BoxLayout(size_hint_y=None, height=dp(20))
        total = item.get('total_pages', 0)
        done = item.get('downloaded_pages', 0)
        info.add_widget(MDLabel(
            text=f"{done}/{total} pages",
            theme_text_color='Custom', text_color=COLORS['text_secondary'], font_style='Caption',
        ))
        info.add_widget(MDIconButton(
            icon='close-circle', theme_text_color='Custom', text_color=COLORS['error'],
            on_release=self.cancel_download, user_font_size=dp(16),
            size_hint_x=None, width=dp(30),
        ))
        self.add_widget(info)

    def cancel_download(self, instance):
        download_manager.cancel_download(self.item['manga_id'], self.item['chapter_id'])


class DownloadsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = COLORS['background']
        self._build_ui()
        Clock.schedule_once(lambda dt: self.refresh_list(), 0.3)
        download_manager.register_callback(self.on_download_update)

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')

        header = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(8))
        header.add_widget(MDLabel(
            text='Download Queue', theme_text_color='Custom',
            text_color=COLORS['primary'], font_style='H6',
        ))
        header.add_widget(MDFlatButton(
            text='Clear Completed', text_color=COLORS['text_secondary'],
            on_release=self.clear_completed,
        ))
        layout.add_widget(header)

        scroll = ScrollView()
        self.list_layout = GridLayout(
            cols=1, spacing=dp(4), padding=dp(8), size_hint_y=None,
        )
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def refresh_list(self):
        self.list_layout.clear_widgets()
        queue = download_manager.get_queue()
        if not queue:
            self.list_layout.add_widget(MDLabel(
                text="No active downloads.", halign='center',
                theme_text_color='Custom', text_color=COLORS['text_secondary'],
                size_hint_y=None, height=dp(100),
            ))
            return
        for item in queue:
            self.list_layout.add_widget(DownloadItem(item))

    def on_download_update(self, manga_id, chapter_id, status, progress):
        Clock.schedule_once(lambda dt: self.refresh_list(), 0)

    def clear_completed(self, instance):
        download_manager.clear_completed()
        self.refresh_list()
