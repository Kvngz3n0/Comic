"""Browse screen - search manga with history and dynamic sources."""
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.metrics import dp

from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.chip import MDChip
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.menu import MDDropdownMenu

from core.config import COLORS
from core.database import db
from core.extension_manager import extension_manager


class BrowseResultCard(MDCard):
    def __init__(self, manga, **kwargs):
        super().__init__(**kwargs)
        self.manga = manga
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(100)
        self.md_bg_color = COLORS['surface']
        self.radius = [dp(8),]
        self.padding = dp(8)
        self.spacing = dp(8)

        info = BoxLayout(orientation='vertical')
        info.add_widget(MDLabel(
            text=manga.get('title', 'Unknown'),
            theme_text_color='Custom', text_color=COLORS['text'],
            font_style='Subtitle1', size_hint_y=0.4,
        ))
        info.add_widget(MDLabel(
            text=manga.get('author', 'Unknown Author')[:30],
            theme_text_color='Custom', text_color=COLORS['text_secondary'],
            font_style='Caption', size_hint_y=0.3,
        ))
        info.add_widget(MDLabel(
            text=manga.get('status', 'Unknown'),
            theme_text_color='Custom', text_color=COLORS['primary'],
            font_style='Overline', size_hint_y=0.3,
        ))
        self.add_widget(info)

        actions = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(40))
        actions.add_widget(MDIconButton(
            icon='heart-outline', theme_text_color='Custom',
            text_color=COLORS['primary'], on_release=self.add_to_library,
        ))
        actions.add_widget(MDIconButton(
            icon='download-outline', theme_text_color='Custom',
            text_color=COLORS['primary'], on_release=self.download_all,
        ))
        self.add_widget(actions)

    def add_to_library(self, instance):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        db.add_to_library(self.manga)
        db.save_chapters(self.manga.get('id'), self.manga.get('chapters', []))
        instance.icon = 'heart'
        if hasattr(app, 'library_screen'):
            app.library_screen.load_library()

    def download_all(self, instance):
        from core.downloader import download_manager
        chapters = db.get_chapters(self.manga.get('id'))
        if not chapters:
            chapters = extension_manager.get_chapters(self.manga.get('source'), self.manga.get('id'))
            db.save_chapters(self.manga.get('id'), chapters)
        for ch in chapters[:3]:
            pages = extension_manager.get_pages(self.manga.get('source'), ch['id'])
            if pages:
                download_manager.queue_chapter(self.manga.get('id'), ch['id'], ch['title'], pages)

    def on_release(self):
        app = self.get_root_window().children[0].children[0]
        if hasattr(app, 'switch_to_manga_detail'):
            app.switch_to_manga_detail(self.manga)


class BrowseScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = COLORS['background']
        self._build_ui()
        Clock.schedule_once(lambda dt: self.load_history(), 0.3)

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))

        search_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))

        self.source_btn = MDRaisedButton(
            text='MangaDex',
            md_bg_color=COLORS['surface'],
            text_color=COLORS['primary'],
            size_hint_x=None,
            width=dp(100),
        )
        self.source_btn.bind(on_release=self.show_source_menu)
        search_box.add_widget(self.source_btn)

        self.search_field = MDTextField(
            hint_text="Search manga...",
            text_color_normal=COLORS['text_secondary'],
            text_color_focus=COLORS['primary'],
            hint_text_color_normal=COLORS['text_secondary'],
            hint_text_color_focus=COLORS['primary'],
            line_color_normal=COLORS['surface_light'],
            line_color_focus=COLORS['primary'],
        )
        self.search_field.bind(on_text_validate=self.do_search)
        search_box.add_widget(self.search_field)

        search_btn = MDIconButton(
            icon='magnify',
            theme_text_color='Custom',
            text_color=COLORS['primary'],
            on_release=self.do_search,
        )
        search_box.add_widget(search_btn)
        layout.add_widget(search_box)

        self.history_box = BoxLayout(
            size_hint_y=None,
            height=dp(40),
            spacing=dp(4),
        )
        layout.add_widget(self.history_box)

        scroll = ScrollView()
        self.results_grid = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(4),
            size_hint_y=None,
        )
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        scroll.add_widget(self.results_grid)
        layout.add_widget(scroll)

        self.add_widget(layout)
        self.source_menu = None

    def show_source_menu(self, instance):
        if self.source_menu:
            self.source_menu.dismiss()

        sources = extension_manager.get_extensions()
        menu_items = [
            {"text": f"{s.get('icon', '')} {s['name']}", "viewclass": "OneLineListItem", 
             "on_release": lambda x=s: self.set_source(x)}
            for s in sources
        ]
        self.source_menu = MDDropdownMenu(
            caller=instance,
            items=menu_items,
            width_mult=4,
        )
        self.source_menu.open()

    def set_source(self, source):
        self.source_btn.text = source['name'][:12]
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        app.current_source = source['id']
        if self.source_menu:
            self.source_menu.dismiss()

    def refresh_sources(self):
        """Refresh source list after repo changes."""
        self.source_menu = None

    def focus_search(self):
        self.search_field.focus = True

    def do_search(self, instance=None):
        query = self.search_field.text.strip()
        if not query:
            return

        db.add_search_history(query)
        self.load_history()

        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        source_id = app.current_source

        self.results_grid.clear_widgets()
        self.results_grid.add_widget(MDLabel(
            text="Searching...",
            halign='center',
            theme_text_color='Custom',
            text_color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(100),
        ))

        def _search(dt):
            results = extension_manager.search(source_id, query)
            self.results_grid.clear_widgets()

            if not results:
                self.results_grid.add_widget(MDLabel(
                    text="No results found.",
                    halign='center',
                    theme_text_color='Custom',
                    text_color=COLORS['text_secondary'],
                    size_hint_y=None,
                    height=dp(100),
                ))
                return

            for manga in results:
                card = BrowseResultCard(manga)
                self.results_grid.add_widget(card)

        Clock.schedule_once(_search, 0.1)

    def load_history(self):
        self.history_box.clear_widgets()
        history = db.get_search_history(limit=10)

        for query in history:
            chip = MDChip(
                text=query[:15],
                text_color=COLORS['text'],
                md_bg_color=COLORS['surface_light'],
                on_release=lambda x, q=query: self.search_from_history(q),
            )
            self.history_box.add_widget(chip)

    def search_from_history(self, query):
        self.search_field.text = query
        self.do_search()
