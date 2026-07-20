"""eBooks screen for EPUB reading."""
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.metrics import dp

from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField

from core.config import COLORS, BASE_DIR
from core.epub_reader import scan_epubs, EPUBReader


class EPUBCard(MDCard):
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
            text=book.get('author', 'Unknown'),
            theme_text_color='Custom', text_color=COLORS['text_secondary'],
            font_style='Caption', size_hint_y=0.3,
        ))
        info.add_widget(MDLabel(
            text=f"{book.get('chapters_count', 0)} chapters",
            theme_text_color='Custom', text_color=COLORS['primary'],
            font_style='Overline', size_hint_y=0.3,
        ))
        self.add_widget(info)

        self.add_widget(MDIconButton(
            icon='book-open-variant', theme_text_color='Custom',
            text_color=COLORS['primary'], on_release=self.open_book,
        ))

    def open_book(self, instance):
        app = self.get_root_window().children[0].children[0]
        if hasattr(app, 'switch_to_ebook_reader'):
            app.switch_to_ebook_reader(self.book)


class EBookReaderScreen(MDScreen):
    """Screen for reading EPUB chapters as text."""
    def __init__(self, book=None, **kwargs):
        super().__init__(**kwargs)
        self.book_data = book
        self.reader = None
        self.current_chapter = 0
        self.md_bg_color = COLORS['background']
        self._build_ui()
        if book:
            Clock.schedule_once(lambda dt: self.load_book(), 0.3)

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')

        # Top bar
        top = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(8))
        top.add_widget(MDIconButton(
            icon='arrow-left', theme_text_color='Custom',
            text_color=COLORS['text'], on_release=self.go_back,
        ))
        self.chapter_label = MDLabel(
            text="", theme_text_color='Custom',
            text_color=COLORS['primary'], halign='center',
        )
        top.add_widget(self.chapter_label)
        layout.add_widget(top)

        # Content
        scroll = ScrollView()
        self.content_label = MDLabel(
            text="", theme_text_color='Custom',
            text_color=COLORS['text'], halign='left',
            valign='top', size_hint_y=None,
            padding=(dp(16), dp(16)),
        )
        self.content_label.bind(texture_size=self.content_label.setter('size'))
        scroll.add_widget(self.content_label)
        layout.add_widget(scroll)

        # Bottom nav
        bottom = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(16), padding=dp(8))
        bottom.add_widget(MDRaisedButton(
            text='Previous', md_bg_color=COLORS['surface_light'],
            text_color=COLORS['primary'], on_release=self.prev_chapter,
        ))
        bottom.add_widget(MDRaisedButton(
            text='Next', md_bg_color=COLORS['primary'],
            text_color=COLORS['background'], on_release=self.next_chapter,
        ))
        layout.add_widget(bottom)

        self.add_widget(layout)

    def load_book(self):
        if self.book_data:
            self.reader = EPUBReader(self.book_data['path'])
            self.show_chapter(0)

    def show_chapter(self, index):
        if self.reader and 0 <= index < len(self.reader.chapters):
            self.current_chapter = index
            ch = self.reader.get_chapter(index)
            self.chapter_label.text = ch['title']
            self.content_label.text = ch['content']

    def next_chapter(self, instance):
        self.show_chapter(self.current_chapter + 1)

    def prev_chapter(self, instance):
        self.show_chapter(self.current_chapter - 1)

    def go_back(self, instance):
        app = self.get_root_window().children[0].children[0]
        app.sm.current = 'ebooks'
        for child in app.sm.children[:]:
            if child.name == 'ebook_reader':
                app.sm.remove_widget(child)


class EBooksScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = COLORS['background']
        self._build_ui()
        Clock.schedule_once(lambda dt: self.scan_books(), 0.3)

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical')

        header = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(8))
        header.add_widget(MDLabel(
            text='eBooks', theme_text_color='Custom',
            text_color=COLORS['primary'], font_style='H6',
        ))
        header.add_widget(MDRaisedButton(
            text='Scan Folder', md_bg_color=COLORS['surface_light'],
            text_color=COLORS['primary'], on_release=self.scan_books,
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

    def scan_books(self, instance=None):
        self.list_layout.clear_widgets()
        books = scan_epubs(BASE_DIR)

        if not books:
            self.list_layout.add_widget(MDLabel(
                text="No EPUB files found.\nPlace .epub files in the app folder.",
                halign='center', theme_text_color='Custom',
                text_color=COLORS['text_secondary'], size_hint_y=None, height=dp(100),
            ))
            return

        for book in books:
            self.list_layout.add_widget(EPUBCard(book))
