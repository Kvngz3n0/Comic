"""Manga detail screen with chapters."""
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.metrics import dp

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog

from core.config import COLORS
from core.database import db
from core.extension_manager import extension_manager
from core.downloader import download_manager


class ChapterItem(MDCard):
    def __init__(self, manga_id, chapter, **kwargs):
        super().__init__(**kwargs)
        self.manga_id = manga_id
        self.chapter = chapter
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(60)
        self.md_bg_color = COLORS['surface']
        self.radius = [dp(4),]
        self.padding = dp(8)
        self.spacing = dp(8)

        # Chapter info
        info = BoxLayout(orientation='vertical')
        info.add_widget(MDLabel(
            text=chapter.get('title', f"Chapter {chapter.get('number', '?')}"),
            theme_text_color='Custom',
            text_color=COLORS['text'],
            font_style='Body1',
            size_hint_y=0.6,
        ))
        info.add_widget(MDLabel(
            text=chapter.get('date_uploaded', '')[:10],
            theme_text_color='Custom',
            text_color=COLORS['text_secondary'],
            font_style='Caption',
            size_hint_y=0.4,
        ))
        self.add_widget(info)

        # Status icons
        status_box = BoxLayout(size_hint_x=None, width=dp(80), spacing=dp(4))

        if chapter.get('is_downloaded'):
            status_box.add_widget(MDIconButton(
                icon='check-circle',
                theme_text_color='Custom',
                text_color=COLORS['success'],
                user_font_size=dp(16),
            ))

        if chapter.get('is_read'):
            status_box.add_widget(MDIconButton(
                icon='eye-check',
                theme_text_color='Custom',
                text_color=COLORS['primary'],
                user_font_size=dp(16),
            ))

        status_box.add_widget(MDIconButton(
            icon='download-outline',
            theme_text_color='Custom',
            text_color=COLORS['primary'],
            on_release=self.download_chapter,
            user_font_size=dp(16),
        ))

        self.add_widget(status_box)

    def download_chapter(self, instance):
        pages = extension_manager.get_pages('mangadex', self.chapter['id'])
        if pages:
            download_manager.queue_chapter(
                self.manga_id, self.chapter['id'], self.chapter['title'], pages
            )
            instance.icon = 'download'
            instance.text_color = COLORS['success']

    def on_release(self):
        app = self.get_root_window().children[0].children[0]
        pages = extension_manager.get_pages('mangadex', self.chapter['id'])
        if pages:
            db.mark_chapter_read(self.manga_id, self.chapter['id'])
            app.switch_to_reader(self.manga_id, self.chapter['id'], pages, self.chapter['title'])


class MangaDetailScreen(MDScreen):
    def __init__(self, manga=None, **kwargs):
        super().__init__(**kwargs)
        self.manga = manga or {}
        self.md_bg_color = COLORS['background']
        self._build_ui()
        Clock.schedule_once(lambda dt: self.load_chapters(), 0.3)

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')

        # Header
        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(200), padding=dp(16))
        header.md_bg_color = COLORS['surface']

        title = MDLabel(
            text=self.manga.get('title', 'Unknown'),
            theme_text_color='Custom',
            text_color=COLORS['primary'],
            font_style='H5',
            halign='center',
        )
        header.add_widget(title)

        author = MDLabel(
            text=self.manga.get('author', 'Unknown Author'),
            theme_text_color='Custom',
            text_color=COLORS['text_secondary'],
            font_style='Subtitle1',
            halign='center',
        )
        header.add_widget(author)

        desc = MDLabel(
            text=self.manga.get('description', 'No description.')[:200],
            theme_text_color='Custom',
            text_color=COLORS['text_secondary'],
            font_style='Caption',
            halign='center',
        )
        header.add_widget(desc)

        # Action buttons
        actions = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8), padding=dp(8))

        self.library_btn = MDRaisedButton(
            text='Add to Library',
            md_bg_color=COLORS['primary'],
            text_color=COLORS['background'],
            on_release=self.toggle_library,
        )
        actions.add_widget(self.library_btn)

        actions.add_widget(MDRaisedButton(
            text='Download All',
            md_bg_color=COLORS['surface_light'],
            text_color=COLORS['primary'],
            on_release=self.download_all,
        ))

        actions.add_widget(MDRaisedButton(
            text='Read',
            md_bg_color=COLORS['surface_light'],
            text_color=COLORS['primary'],
            on_release=self.read_first,
        ))

        header.add_widget(actions)
        layout.add_widget(header)

        # Chapters list
        scroll = ScrollView()
        self.chapters_list = GridLayout(
            cols=1,
            spacing=dp(4),
            padding=dp(8),
            size_hint_y=None,
        )
        self.chapters_list.bind(minimum_height=self.chapters_list.setter('height'))
        scroll.add_widget(self.chapters_list)
        layout.add_widget(scroll)

        self.add_widget(layout)

        # Update library button state
        if db.is_in_library(self.manga.get('id')):
            self.library_btn.text = 'In Library'
            self.library_btn.md_bg_color = COLORS['success']

    def load_chapters(self):
        self.chapters_list.clear_widgets()
        manga_id = self.manga.get('id')
        source = self.manga.get('source', 'mangadex')

        # Try DB first
        chapters = db.get_chapters(manga_id)
        if not chapters:
            chapters = extension_manager.get_chapters(source, manga_id)
            db.save_chapters(manga_id, chapters)

        if not chapters:
            self.chapters_list.add_widget(MDLabel(
                text="No chapters available.",
                halign='center',
                theme_text_color='Custom',
                text_color=COLORS['text_secondary'],
                size_hint_y=None,
                height=dp(100),
            ))
            return

        for ch in chapters:
            item = ChapterItem(manga_id, ch)
            self.chapters_list.add_widget(item)

    def toggle_library(self, instance):
        manga_id = self.manga.get('id')
        if db.is_in_library(manga_id):
            db.remove_from_library(manga_id)
            instance.text = 'Add to Library'
            instance.md_bg_color = COLORS['primary']
        else:
            db.add_to_library(self.manga)
            db.save_chapters(manga_id, extension_manager.get_chapters(self.manga.get('source', 'mangadex'), manga_id))
            instance.text = 'In Library'
            instance.md_bg_color = COLORS['success']

    def download_all(self, instance):
        chapters = db.get_chapters(self.manga.get('id'))
        for ch in chapters[:5]:  # Limit to 5 for demo
            pages = extension_manager.get_pages(self.manga.get('source', 'mangadex'), ch['id'])
            if pages:
                download_manager.queue_chapter(self.manga.get('id'), ch['id'], ch['title'], pages)

    def read_first(self, instance):
        chapters = db.get_chapters(self.manga.get('id'))
        if chapters:
            ch = chapters[-1]  # First chapter (lowest number)
            pages = extension_manager.get_pages(self.manga.get('source', 'mangadex'), ch['id'])
            if pages:
                app = self.get_root_window().children[0].children[0]
                app.switch_to_reader(self.manga.get('id'), ch['id'], pages, ch['title'])
