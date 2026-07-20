"""Library screen - saved manga collection."""
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.metrics import dp

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu

from core.config import COLORS
from core.database import db


class MangaCard(MDCard):
    def __init__(self, manga, **kwargs):
        super().__init__(**kwargs)
        self.manga = manga
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(220)
        self.md_bg_color = COLORS['surface']
        self.radius = [dp(8),]
        self.elevation = 2

        # Cover placeholder
        cover = BoxLayout(
            size_hint_y=0.75,
        )
        cover.add_widget(MDLabel(
            text=manga.get('title', 'Unknown')[:2].upper(),
            halign='center',
            theme_text_color='Custom',
            text_color=COLORS['primary'],
            font_style='H4',
        ))
        self.add_widget(cover)

        # Title
        self.add_widget(MDLabel(
            text=manga.get('title', 'Unknown')[:20] + ('...' if len(manga.get('title', '')) > 20 else ''),
            halign='center',
            theme_text_color='Custom',
            text_color=COLORS['text'],
            size_hint_y=0.15,
            font_style='Caption',
        ))

        # Status
        status_text = "Downloaded" if manga.get('is_downloaded') else "In Library"
        self.add_widget(MDLabel(
            text=status_text,
            halign='center',
            theme_text_color='Custom',
            text_color=COLORS['text_secondary'],
            size_hint_y=0.1,
            font_style='Overline',
        ))

    def on_release(self):
        app = self.get_root_window().children[0].children[0]
        if hasattr(app, 'switch_to_manga_detail'):
            app.switch_to_manga_detail(self.manga)


class LibraryScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = COLORS['background']
        self._build_ui()
        Clock.schedule_once(lambda dt: self.load_library(), 0.5)

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')

        # Filter chips
        filter_box = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(8))
        self.filter_btn = MDFlatButton(
            text='All',
            text_color=COLORS['primary'],
            md_bg_color=COLORS['surface'],
        )
        self.filter_btn.bind(on_release=self.show_filter_menu)
        filter_box.add_widget(self.filter_btn)
        layout.add_widget(filter_box)

        # Grid
        scroll = ScrollView()
        self.grid = GridLayout(
            cols=3 if not self.get_root_window() else (3 if self.get_root_window().width < dp(600) else 5),
            spacing=dp(8),
            padding=dp(8),
            size_hint_y=None,
        )
        self.grid.bind(minimum_height=self.grid.setter('height'))
        scroll.add_widget(self.grid)
        layout.add_widget(scroll)

        self.add_widget(layout)

        self.filter_menu = None

    def show_filter_menu(self, instance):
        if not self.filter_menu:
            menu_items = [
                {"text": f"{cat}", "viewclass": "OneLineListItem", "on_release": lambda x=cat: self.set_filter(x)}
                for cat in ['All', 'Reading', 'Downloaded', 'Completed']
            ]
            self.filter_menu = MDDropdownMenu(
                caller=instance,
                items=menu_items,
                width_mult=4,
            )
        self.filter_menu.open()

    def set_filter(self, category):
        self.filter_btn.text = category
        if self.filter_menu:
            self.filter_menu.dismiss()
        self.load_library(category if category != 'All' else None)

    def load_library(self, category=None):
        self.grid.clear_widgets()
        manga_list = db.get_library(category)

        if not manga_list:
            self.grid.add_widget(MDLabel(
                text="No manga in library yet.\nBrowse and add some!",
                halign='center',
                theme_text_color='Custom',
                text_color=COLORS['text_secondary'],
                size_hint_y=None,
                height=dp(200),
            ))
            return

        for manga in manga_list:
            card = MangaCard(manga)
            self.grid.add_widget(card)
