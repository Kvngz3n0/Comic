"""Main KivyMD App for Imperial Reader."""
import os
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.properties import StringProperty

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

from core.config import COLORS, IS_ANDROID, IS_DESKTOP
from core.database import db

from ui.screens.library import LibraryScreen
from ui.screens.browse import BrowseScreen
from ui.screens.downloads import DownloadsScreen
from ui.screens.ebooks import EBooksScreen, EBookReaderScreen
from ui.screens.local_files import LocalFilesScreen
from ui.screens.settings import SettingsScreen


class ImperialReaderApp(MDApp):
    current_source = StringProperty('mangadex')

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Amber"
        self.theme_cls.primary_hue = "400"
        self.theme_cls.material_style = "M3"

        if IS_DESKTOP:
            Window.size = (400, 800)
            Window.maximize()

        root = MDBoxLayout(orientation='vertical')

        self.toolbar = MDTopAppBar(
            title="[b]Imperial Reader[/b]",
            elevation=4,
            md_bg_color=COLORS['surface'],
            specific_text_color=COLORS['primary'],
            left_action_items=[['crown', lambda x: None]],
            right_action_items=[
                ['magnify', lambda x: self.show_search()],
                ['dots-vertical', lambda x: self.show_menu()],
            ]
        )
        root.add_widget(self.toolbar)

        self.sm = MDScreenManager()

        self.bottom_nav = MDBottomNavigation(
            panel_color=COLORS['surface'],
            selected_color_background=COLORS['primary'],
            text_color_active=COLORS['primary'],
            text_color_normal=COLORS['text_secondary'],
        )

        # Library Tab
        self.library_tab = MDBottomNavigationItem(name='library', text='Library', icon='book-open-variant')
        self.library_screen = LibraryScreen(name='library_content')
        self.library_tab.add_widget(self.library_screen)
        self.bottom_nav.add_widget(self.library_tab)

        # Browse Tab
        self.browse_tab = MDBottomNavigationItem(name='browse', text='Browse', icon='magnify')
        self.browse_screen = BrowseScreen(name='browse_content')
        self.browse_tab.add_widget(self.browse_screen)
        self.bottom_nav.add_widget(self.browse_tab)

        # eBooks Tab
        self.ebooks_tab = MDBottomNavigationItem(name='ebooks', text='eBooks', icon='book')
        self.ebooks_screen = EBooksScreen(name='ebooks_content')
        self.ebooks_tab.add_widget(self.ebooks_screen)
        self.bottom_nav.add_widget(self.ebooks_tab)

        # Local Tab
        self.local_tab = MDBottomNavigationItem(name='local', text='Local', icon='folder')
        self.local_screen = LocalFilesScreen(name='local_content')
        self.local_tab.add_widget(self.local_screen)
        self.bottom_nav.add_widget(self.local_tab)

        # Downloads Tab
        self.downloads_tab = MDBottomNavigationItem(name='downloads', text='Downloads', icon='download')
        self.downloads_screen = DownloadsScreen(name='downloads_content')
        self.downloads_tab.add_widget(self.downloads_screen)
        self.bottom_nav.add_widget(self.downloads_tab)

        # Settings Tab
        self.settings_tab = MDBottomNavigationItem(name='settings', text='More', icon='cog')
        self.settings_screen = SettingsScreen(name='settings_content')
        self.settings_tab.add_widget(self.settings_screen)
        self.bottom_nav.add_widget(self.settings_tab)

        self.sm.add_widget(self.bottom_nav)
        root.add_widget(self.sm)

        Clock.schedule_interval(self._refresh_downloads, 2)

        return root

    def _refresh_downloads(self, dt):
        if hasattr(self, 'downloads_screen'):
            self.downloads_screen.refresh_list()

    def show_search(self):
        self.bottom_nav.switch_tab('browse')
        self.browse_screen.focus_search()

    def show_menu(self):
        pass

    def switch_to_manga_detail(self, manga):
        from ui.screens.manga_detail import MangaDetailScreen
        screen = MangaDetailScreen(name='manga_detail', manga=manga)
        self.sm.add_widget(screen)
        self.sm.current = 'manga_detail'
        self.toolbar.title = manga.get('title', 'Details')[:30]
        self.toolbar.left_action_items = [['arrow-left', lambda x: self.back_to_library()]]

    def back_to_library(self):
        self.sm.current = 'library'
        self.toolbar.title = "[b]Imperial Reader[/b]"
        self.toolbar.left_action_items = [['crown', lambda x: None]]
        for child in self.sm.children[:]:
            if child.name == 'manga_detail':
                self.sm.remove_widget(child)

    def switch_to_reader(self, manga_id, chapter_id, pages, title=""):
        from ui.screens.reader import ReaderScreen
        screen = ReaderScreen(name='reader', manga_id=manga_id, chapter_id=chapter_id, pages=pages, title=title)
        self.sm.add_widget(screen)
        self.sm.current = 'reader'
        self.toolbar.opacity = 0

    def back_from_reader(self):
        self.toolbar.opacity = 1
        self.sm.current = 'manga_detail'
        for child in self.sm.children[:]:
            if child.name == 'reader':
                self.sm.remove_widget(child)

    def switch_to_ebook_reader(self, book):
        screen = EBookReaderScreen(name='ebook_reader', book=book)
        self.sm.add_widget(screen)
        self.sm.current = 'ebook_reader'
        self.toolbar.opacity = 0
