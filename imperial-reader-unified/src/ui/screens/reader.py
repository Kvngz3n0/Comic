"""Full-screen manga reader with tap controls."""
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.slider import Slider
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.animation import Animation

from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDIconButton, MDFlatButton
from kivymd.uix.label import MDLabel

from core.config import COLORS
from core.database import db


class ReaderScreen(MDScreen):
    manga_id = StringProperty('')
    chapter_id = StringProperty('')
    pages = ListProperty([])
    current_page = NumericProperty(0)

    def __init__(self, manga_id='', chapter_id='', pages=None, title="", **kwargs):
        super().__init__(**kwargs)
        self.manga_id = manga_id
        self.chapter_id = chapter_id
        self.pages = pages or []
        self.chapter_title = title
        self.md_bg_color = COLORS['background']
        self._controls_visible = True
        self._build_ui()

    def _build_ui(self):
        layout = RelativeLayout()

        self.page_image = AsyncImage(
            source=self.pages[0] if self.pages else '',
            allow_stretch=True,
            keep_ratio=True,
        )
        layout.add_widget(self.page_image)

        self._add_tap_zones(layout)

        self.top_bar = BoxLayout(
            size_hint_y=None, height=dp(56), pos_hint={'top': 1},
            padding=dp(8), spacing=dp(8),
        )
        self.top_bar.md_bg_color = [0, 0, 0, 0.7]

        back_btn = MDIconButton(
            icon='arrow-left', theme_text_color='Custom', text_color=COLORS['text'],
            on_release=self.go_back,
        )
        self.top_bar.add_widget(back_btn)

        self.title_label = MDLabel(
            text=self.chapter_title[:40],
            theme_text_color='Custom', text_color=COLORS['text'], halign='left',
        )
        self.top_bar.add_widget(self.title_label)

        self.page_label = MDLabel(
            text=f"1 / {len(self.pages)}",
            theme_text_color='Custom', text_color=COLORS['primary'],
            halign='right', size_hint_x=None, width=dp(80),
        )
        self.top_bar.add_widget(self.page_label)
        layout.add_widget(self.top_bar)

        self.bottom_bar = BoxLayout(
            size_hint_y=None, height=dp(80), pos_hint={'y': 0},
            padding=dp(16), orientation='vertical',
        )
        self.bottom_bar.md_bg_color = [0, 0, 0, 0.7]

        self.slider = Slider(
            min=0, max=max(len(self.pages) - 1, 1), value=0,
            cursor_color=COLORS['primary'],
            background_color=COLORS['surface_light'],
            value_track_color=COLORS['primary'], value_track=True,
        )
        self.slider.bind(value=self.on_slider_change)
        self.bottom_bar.add_widget(self.slider)

        nav_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(16))
        nav_box.add_widget(MDFlatButton(text='Prev', text_color=COLORS['primary'], on_release=self.prev_page))
        nav_box.add_widget(MDFlatButton(text='Next', text_color=COLORS['primary'], on_release=self.next_page))
        self.bottom_bar.add_widget(nav_box)
        layout.add_widget(self.bottom_bar)

        self.add_widget(layout)

    def _add_tap_zones(self, layout):
        left = BoxLayout(size_hint=(0.3, 1), pos_hint={'x': 0, 'y': 0})
        left.bind(on_touch_down=self._on_left_tap)
        layout.add_widget(left)

        center = BoxLayout(size_hint=(0.4, 1), pos_hint={'center_x': 0.5, 'y': 0})
        center.bind(on_touch_down=self._on_center_tap)
        layout.add_widget(center)

        right = BoxLayout(size_hint=(0.3, 1), pos_hint={'right': 1, 'y': 0})
        right.bind(on_touch_down=self._on_right_tap)
        layout.add_widget(right)

    def _on_left_tap(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.prev_page(None)
            return True

    def _on_center_tap(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.toggle_controls()
            return True

    def _on_right_tap(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.next_page(None)
            return True

    def toggle_controls(self):
        self._controls_visible = not self._controls_visible
        Animation(opacity=1 if self._controls_visible else 0, duration=0.2).start(self.top_bar)
        Animation(opacity=1 if self._controls_visible else 0, duration=0.2).start(self.bottom_bar)

    def on_slider_change(self, instance, value):
        page = int(value)
        if page != self.current_page and 0 <= page < len(self.pages):
            self.current_page = page
            self._update_page()

    def _update_page(self):
        if 0 <= self.current_page < len(self.pages):
            self.page_image.source = self.pages[self.current_page]
            self.page_label.text = f"{self.current_page + 1} / {len(self.pages)}"
            self.slider.value = self.current_page
            db.mark_chapter_read(self.manga_id, self.chapter_id, self.current_page)

    def next_page(self, instance):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self._update_page()

    def prev_page(self, instance):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_page()

    def go_back(self, instance):
        app = self.get_root_window().children[0].children[0]
        app.back_from_reader()
