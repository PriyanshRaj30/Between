"""
Calculator UI — Kivy screen that looks and feels like a real calculator.
Design: Realistic physical calculator with dark body, light keys.
Unlocks private mode via secret sequence without any visible hint.
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.app import App
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp, sp

from mobile.calculator.calculator_logic import CalculatorLogic


# ──────────────────────────────────────────────────────────────
#  Color Palette  (physical calculator aesthetic)
# ──────────────────────────────────────────────────────────────
BODY_COLOR        = (0.10, 0.10, 0.12, 1)     # Very dark charcoal
DISPLAY_BG        = (0.06, 0.06, 0.08, 1)     # Near-black display
DISPLAY_TEXT      = (0.95, 1.00, 0.90, 1)     # Slightly warm white

KEY_NUMBER_BG     = (0.22, 0.22, 0.26, 1)     # Dark grey
KEY_OP_BG         = (0.90, 0.50, 0.10, 1)     # Amber / orange operator keys
KEY_UTIL_BG       = (0.30, 0.30, 0.35, 1)     # Medium grey utility keys
KEY_EQUALS_BG     = (0.92, 0.55, 0.08, 1)     # Bright amber for equals

KEY_NUMBER_TEXT   = (0.95, 0.95, 0.95, 1)
KEY_OP_TEXT       = (1.00, 1.00, 1.00, 1)
KEY_UTIL_TEXT     = (0.95, 0.95, 0.95, 1)

KEY_PRESSED_BG    = (0.40, 0.40, 0.45, 1)     # Pressed highlight


class CalcButton(Button):
    """
    A single calculator button with rounded corners and press animation.
    """

    def __init__(self, label, bg_color, text_color, **kwargs):
        super().__init__(**kwargs)
        self.text = label
        self.base_color = bg_color
        self.pressed_color = KEY_PRESSED_BG
        self.background_color = (0, 0, 0, 0)  # transparent (we draw manually)
        self.background_normal = ""
        self.background_down = ""
        self.color = text_color
        self.font_size = sp(22)
        self.bold = True
        self.size_hint = (1, 1)

        with self.canvas.before:
            self._bg_color_instr = Color(*bg_color)
            self._bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(10)]
            )

        self.bind(pos=self._update_bg, size=self._update_bg)
        self.bind(on_press=self._on_press, on_release=self._on_release)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _on_press(self, *args):
        self._bg_color_instr.rgba = self.pressed_color

    def _on_release(self, *args):
        self._bg_color_instr.rgba = self.base_color


class CalculatorScreen(Screen):
    """
    Calculator screen — the default/visible mode.
    Appears as a fully-functional calculator to any observer.
    Secret sequence: 7 → 3 → 9 → 1 → =
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ── Calculator logic ──────────────────────────────────
        self.logic = CalculatorLogic(on_secret_detected=self._unlock_private_mode)

        # ── Layout ────────────────────────────────────────────
        self._build_ui()

    def _build_ui(self):
        # Root layout
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))

        # Draw body background
        with root.canvas.before:
            Color(*BODY_COLOR)
            self._body_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *a: setattr(self._body_rect, "pos", root.pos))
        root.bind(size=lambda *a: setattr(self._body_rect, "size", root.size))

        # ── Display ───────────────────────────────────────────
        display_container = BoxLayout(
            size_hint=(1, 0.30),
            padding=[dp(16), dp(12), dp(16), dp(12)],
        )
        with display_container.canvas.before:
            Color(*DISPLAY_BG)
            self._display_rect = RoundedRectangle(
                pos=display_container.pos,
                size=display_container.size,
                radius=[dp(16)],
            )
        display_container.bind(
            pos=lambda *a: setattr(self._display_rect, "pos", display_container.pos),
            size=lambda *a: setattr(self._display_rect, "size", display_container.size),
        )

        self.display_label = Label(
            text="0",
            font_size=sp(52),
            color=DISPLAY_TEXT,
            halign="right",
            valign="bottom",
            bold=True,
        )
        self.display_label.bind(
            size=lambda *a: setattr(self.display_label, "text_size", self.display_label.size)
        )
        display_container.add_widget(self.display_label)
        root.add_widget(display_container)

        # ── Button Grid ───────────────────────────────────────
        button_layout = GridLayout(
            cols=4,
            spacing=dp(6),
            size_hint=(1, 0.70),
        )

        # Button definitions: (label, bg_color, text_color)
        buttons = [
            # Row 1
            ("C",  KEY_UTIL_BG,  KEY_UTIL_TEXT),
            ("±",  KEY_UTIL_BG,  KEY_UTIL_TEXT),
            ("%",  KEY_UTIL_BG,  KEY_UTIL_TEXT),
            ("÷",  KEY_OP_BG,    KEY_OP_TEXT),
            # Row 2
            ("7",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("8",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("9",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("×",  KEY_OP_BG,    KEY_OP_TEXT),
            # Row 3
            ("4",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("5",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("6",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("−",  KEY_OP_BG,    KEY_OP_TEXT),
            # Row 4
            ("1",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("2",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("3",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("+",  KEY_OP_BG,    KEY_OP_TEXT),
            # Row 5 — note: 0 is wider (spans 2 cols) — we'll fake with standard grid
            ("⌫",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("0",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            (".",  KEY_NUMBER_BG, KEY_NUMBER_TEXT),
            ("=",  KEY_EQUALS_BG, KEY_OP_TEXT),
        ]

        for label, bg, fg in buttons:
            btn = CalcButton(label=label, bg_color=bg, text_color=fg)
            btn.bind(on_release=lambda b: self._on_button(b.text))
            button_layout.add_widget(btn)

        root.add_widget(button_layout)
        self.add_widget(root)

    def _on_button(self, key: str):
        """Delegate to logic, update display."""
        new_display = self.logic.press(key)
        self._set_display(new_display)

    def _set_display(self, text: str):
        """Update display with auto-sizing font."""
        length = len(text)
        if length <= 5:
            self.display_label.font_size = sp(52)
        elif length <= 9:
            self.display_label.font_size = sp(40)
        elif length <= 12:
            self.display_label.font_size = sp(30)
        else:
            self.display_label.font_size = sp(22)
        self.display_label.text = text

    def _unlock_private_mode(self):
        """
        Secret sequence was detected.
        Quietly transition to private chat — no visual hint that this happened.
        """
        app = App.get_running_app()
        if app:
            app.switch_to_private()
