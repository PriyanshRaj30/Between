"""
Private Chat UI — the secret messaging interface.
Accessible only after entering the correct sequence on the calculator.

Design: Clean dark chat interface with:
- Status bar showing partner's online state
- Scrollable message bubbles (mine right / theirs left)
- Input bar with send button
- Exit button that returns to calculator
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.animation import Animation
from kivy.core.window import Window

from mobile.private_chat.chat_controller import ChatController

# ── Color Palette ─────────────────────────────────────────────────────────────
BG_COLOR          = (0.06, 0.06, 0.10, 1)      # Deep dark blue-black
HEADER_BG         = (0.08, 0.08, 0.13, 1)
HEADER_TEXT       = (0.95, 0.95, 0.95, 1)

MY_BUBBLE_BG      = (0.20, 0.45, 0.85, 1)      # Vivid blue — my messages
MY_BUBBLE_TEXT    = (1.00, 1.00, 1.00, 1)

THEIR_BUBBLE_BG   = (0.18, 0.18, 0.24, 1)      # Dark grey — their messages
THEIR_BUBBLE_TEXT = (0.92, 0.92, 0.92, 1)

INPUT_BG          = (0.12, 0.12, 0.18, 1)
INPUT_TEXT        = (0.95, 0.95, 0.95, 1)
PLACEHOLDER_TEXT  = (0.45, 0.45, 0.55, 1)

SEND_BTN_COLOR    = (0.20, 0.45, 0.85, 1)
EXIT_BTN_COLOR    = (0.28, 0.28, 0.35, 1)

ONLINE_DOT        = (0.20, 0.85, 0.45, 1)      # Green
OFFLINE_DOT       = (0.55, 0.55, 0.60, 1)      # Grey

STATUS_TEXT_ONLINE  = (0.20, 0.85, 0.45, 1)
STATUS_TEXT_OFFLINE = (0.55, 0.55, 0.60, 1)

TIME_COLOR        = (0.45, 0.45, 0.55, 1)


class MessageBubble(BoxLayout):
    """
    A single message bubble. Aligns right for own messages, left for partner's.
    """

    def __init__(self, text: str, is_mine: bool, timestamp: str = "", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.padding = [dp(12), dp(4)]
        self.spacing = dp(2)

        bg_color = MY_BUBBLE_BG if is_mine else THEIR_BUBBLE_BG
        text_color = MY_BUBBLE_TEXT if is_mine else THEIR_BUBBLE_TEXT

        # Outer row aligns bubble horizontally
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
        )

        if is_mine:
            row.add_widget(Widget())  # Spacer left

        # Bubble label
        bubble = Label(
            text=text,
            font_size=sp(16),
            color=text_color,
            markup=True,
            halign="left",
            valign="middle",
            padding=[dp(14), dp(10)],
            size_hint=(None, None),
        )
        bubble.text_size = (Window.width * 0.65, None)
        bubble.bind(texture_size=lambda *a: self._set_bubble_size(bubble, bg_color, row, is_mine))
        row.add_widget(bubble)

        if not is_mine:
            row.add_widget(Widget())  # Spacer right

        self.add_widget(row)

        # Timestamp
        if timestamp:
            ts_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(18))
            ts_label = Label(
                text=timestamp,
                font_size=sp(10),
                color=TIME_COLOR,
                halign="right" if is_mine else "left",
                size_hint=(1, 1),
            )
            ts_label.bind(size=lambda *a: setattr(ts_label, "text_size", ts_label.size))
            ts_row.add_widget(ts_label)
            self.add_widget(ts_row)

        self.height = dp(70)  # Will be updated when bubble sizes

    def _set_bubble_size(self, label, bg_color, row, is_mine):
        w = label.texture_size[0] + dp(28)
        h = label.texture_size[1] + dp(20)
        label.size = (w, h)
        label.height = h
        row.height = h
        self.height = h + dp(24)  # Extra for timestamp/padding

        label.canvas.before.clear()
        with label.canvas.before:
            Color(*bg_color)
            RoundedRectangle(pos=label.pos, size=label.size, radius=[dp(16)])
        label.bind(
            pos=lambda *a: self._redraw_bubble(label, bg_color),
        )

    def _redraw_bubble(self, label, bg_color):
        label.canvas.before.clear()
        with label.canvas.before:
            Color(*bg_color)
            RoundedRectangle(pos=label.pos, size=label.size, radius=[dp(16)])


class LoginPanel(BoxLayout):
    """
    Login panel shown before the chat if not authenticated.
    """

    def __init__(self, on_login, **kwargs):
        super().__init__(**kwargs)
        self.on_login_callback = on_login
        self.orientation = "vertical"
        self.padding = dp(24)
        self.spacing = dp(16)

        with self.canvas.before:
            Color(*BG_COLOR)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg, "pos", self.pos))
        self.bind(size=lambda *a: setattr(self._bg, "size", self.size))

        self.add_widget(Widget(size_hint_y=0.2))

        title = Label(
            text="🔐  Private Mode",
            font_size=sp(26),
            color=HEADER_TEXT,
            bold=True,
            size_hint_y=None,
            height=dp(50),
        )
        self.add_widget(title)

        subtitle = Label(
            text="Enter your credentials to continue",
            font_size=sp(14),
            color=(0.55, 0.55, 0.65, 1),
            size_hint_y=None,
            height=dp(30),
        )
        self.add_widget(subtitle)

        self.username_input = self._make_input("Username", multiline=False)
        self.password_input = self._make_input("Password", password=True, multiline=False)
        self.passphrase_input = self._make_input("Shared encryption passphrase", multiline=False)

        self.add_widget(self.username_input)
        self.add_widget(self.password_input)
        self.add_widget(self.passphrase_input)

        self.error_label = Label(
            text="",
            font_size=sp(13),
            color=(0.9, 0.3, 0.3, 1),
            size_hint_y=None,
            height=dp(30),
        )
        self.add_widget(self.error_label)

        btn = Button(
            text="Enter",
            size_hint=(1, None),
            height=dp(50),
            font_size=sp(18),
            bold=True,
            background_color=(0, 0, 0, 0),
            color=MY_BUBBLE_TEXT,
        )
        with btn.canvas.before:
            Color(*SEND_BTN_COLOR)
            self._btn_bg = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(12)])
        btn.bind(
            pos=lambda *a: setattr(self._btn_bg, "pos", btn.pos),
            size=lambda *a: setattr(self._btn_bg, "size", btn.size),
        )
        btn.bind(on_release=self._do_login)
        self.add_widget(btn)

        self.add_widget(Widget(size_hint_y=0.3))

    def _make_input(self, hint, **kwargs) -> TextInput:
        inp = TextInput(
            hint_text=hint,
            size_hint=(1, None),
            height=dp(48),
            font_size=sp(16),
            foreground_color=INPUT_TEXT,
            hint_text_color=PLACEHOLDER_TEXT,
            background_color=INPUT_BG,
            cursor_color=MY_BUBBLE_BG,
            padding=[dp(14), dp(12)],
            **kwargs,
        )
        return inp

    def _do_login(self, *args):
        self.error_label.text = "Connecting..."
        self.on_login_callback(
            self.username_input.text.strip(),
            self.password_input.text,
            self.passphrase_input.text,
        )

    def show_error(self, msg: str):
        self.error_label.text = msg


class PrivateChatScreen(Screen):
    """
    The private chat screen.
    Shows login panel first if not authenticated.
    Transitions to chat view after successful login.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._messages: list[dict] = []
        self._partner_online = False

        # Controller
        self.controller = ChatController(
            on_message_received=self._on_message_received,
            on_partner_status=self._on_partner_status,
            on_login_result=self._on_login_result,
        )

        self._build_ui()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        self._root = BoxLayout(orientation="vertical")

        with self._root.canvas.before:
            Color(*BG_COLOR)
            self._bg = Rectangle(pos=self._root.pos, size=self._root.size)
        self._root.bind(
            pos=lambda *a: setattr(self._bg, "pos", self._root.pos),
            size=lambda *a: setattr(self._bg, "size", self._root.size),
        )

        # Decide initial view
        if self.controller.is_logged_in:
            self._show_chat_view()
        else:
            self._show_login_view()

        self.add_widget(self._root)

    def _show_login_view(self):
        self._root.clear_widgets()
        self._login_panel = LoginPanel(on_login=self._do_login)
        self._root.add_widget(self._login_panel)

    def _show_chat_view(self):
        self._root.clear_widgets()
        self._build_chat_ui()
        # Load history
        self.controller.load_history(self._load_history_callback)
        # Connect WS
        self.controller.connect_ws()

    def _build_chat_ui(self):
        """Build the main chat interface."""

        # ── Header ─────────────────────────────────────────────
        header = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(60),
            padding=[dp(12), dp(10)],
            spacing=dp(10),
        )
        with header.canvas.before:
            Color(*HEADER_BG)
            self._header_rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(
            pos=lambda *a: setattr(self._header_rect, "pos", header.pos),
            size=lambda *a: setattr(self._header_rect, "size", header.size),
        )

        # Exit button
        exit_btn = Button(
            text="←",
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            font_size=sp(22),
            bold=True,
            background_color=(0, 0, 0, 0),
            color=HEADER_TEXT,
        )
        with exit_btn.canvas.before:
            Color(*EXIT_BTN_COLOR)
            self._exit_bg = RoundedRectangle(pos=exit_btn.pos, size=exit_btn.size, radius=[dp(10)])
        exit_btn.bind(
            pos=lambda *a: setattr(self._exit_bg, "pos", exit_btn.pos),
            size=lambda *a: setattr(self._exit_bg, "size", exit_btn.size),
        )
        exit_btn.bind(on_release=self._exit_to_calculator)
        header.add_widget(exit_btn)

        # Title + status
        title_col = BoxLayout(orientation="vertical", size_hint=(1, 1))

        title_label = Label(
            text="Private",
            font_size=sp(18),
            bold=True,
            color=HEADER_TEXT,
            halign="left",
            size_hint=(1, None),
            height=dp(24),
        )
        title_label.bind(size=lambda *a: setattr(title_label, "text_size", title_label.size))
        title_col.add_widget(title_label)

        self._status_label = Label(
            text="● Offline",
            font_size=sp(12),
            color=STATUS_TEXT_OFFLINE,
            halign="left",
            size_hint=(1, None),
            height=dp(16),
        )
        self._status_label.bind(
            size=lambda *a: setattr(self._status_label, "text_size", self._status_label.size)
        )
        title_col.add_widget(self._status_label)
        header.add_widget(title_col)

        self._root.add_widget(header)

        # ── Message list ───────────────────────────────────────
        self._scroll_view = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(3),
            scroll_type=["bars", "content"],
        )
        self._messages_layout = GridLayout(
            cols=1,
            size_hint_y=None,
            spacing=dp(4),
            padding=[dp(8), dp(8)],
        )
        self._messages_layout.bind(
            minimum_height=self._messages_layout.setter("height")
        )
        self._scroll_view.add_widget(self._messages_layout)
        self._root.add_widget(self._scroll_view)

        # ── Input bar ──────────────────────────────────────────
        input_bar = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(64),
            padding=[dp(12), dp(10)],
            spacing=dp(10),
        )
        with input_bar.canvas.before:
            Color(*HEADER_BG)
            self._input_bar_rect = Rectangle(pos=input_bar.pos, size=input_bar.size)
        input_bar.bind(
            pos=lambda *a: setattr(self._input_bar_rect, "pos", input_bar.pos),
            size=lambda *a: setattr(self._input_bar_rect, "size", input_bar.size),
        )

        self._text_input = TextInput(
            hint_text="Type a message...",
            multiline=False,
            size_hint=(1, None),
            height=dp(44),
            font_size=sp(16),
            foreground_color=INPUT_TEXT,
            hint_text_color=PLACEHOLDER_TEXT,
            background_color=INPUT_BG,
            cursor_color=MY_BUBBLE_BG,
            padding=[dp(14), dp(10)],
        )
        self._text_input.bind(on_text_validate=self._send_message)
        input_bar.add_widget(self._text_input)

        send_btn = Button(
            text="➤",
            size_hint=(None, None),
            size=(dp(44), dp(44)),
            font_size=sp(20),
            bold=True,
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
        )
        with send_btn.canvas.before:
            Color(*SEND_BTN_COLOR)
            self._send_bg = RoundedRectangle(pos=send_btn.pos, size=send_btn.size, radius=[dp(22)])
        send_btn.bind(
            pos=lambda *a: setattr(self._send_bg, "pos", send_btn.pos),
            size=lambda *a: setattr(self._send_bg, "size", send_btn.size),
        )
        send_btn.bind(on_release=self._send_message)
        input_bar.add_widget(send_btn)

        self._root.add_widget(input_bar)

    # ── Event Handlers ────────────────────────────────────────────────────────

    def on_enter(self):
        """Called each time we switch to this screen."""
        if not self.controller.is_logged_in:
            self._show_login_view()
        else:
            # Already logged in — reconnect WS if needed
            self.controller.connect_ws()

    def on_leave(self):
        """Called when leaving this screen."""
        pass  # Keep WS alive for background notifications

    def _do_login(self, username: str, password: str, passphrase: str) -> None:
        if not username or not password or not passphrase:
            self._login_panel.show_error("All fields are required")
            return
        self.controller.login(username, password, passphrase)

    def _on_login_result(self, success: bool, message: str) -> None:
        if success:
            self._show_chat_view()
        else:
            # Show login panel (covers both: initial failure and session expiry)
            self._show_login_view()
            if hasattr(self, "_login_panel"):
                self._login_panel.show_error(message)

    def _on_message_received(self, msg: dict) -> None:
        """Add a new message bubble to the chat."""
        self._add_message_bubble(msg)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.1)

    def _on_partner_status(self, online: bool) -> None:
        self._partner_online = online
        if hasattr(self, "_status_label"):
            if online:
                self._status_label.text = "● Online"
                self._status_label.color = STATUS_TEXT_ONLINE
            else:
                self._status_label.text = "● Offline"
                self._status_label.color = STATUS_TEXT_OFFLINE

    def _load_history_callback(self, messages: list) -> None:
        """Load historical messages into the chat view."""
        for msg in messages:
            self._add_message_bubble(msg)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.2)

    def _add_message_bubble(self, msg: dict) -> None:
        text = msg.get("text", "")
        is_mine = msg.get("is_mine", False)

        # Format timestamp
        timestamp = ""
        created = msg.get("created_at", "")
        if created:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                timestamp = dt.strftime("%H:%M")
            except Exception:
                timestamp = ""

        bubble = MessageBubble(
            text=text,
            is_mine=is_mine,
            timestamp=timestamp,
        )
        self._messages_layout.add_widget(bubble)

    def _send_message(self, *args) -> None:
        text = self._text_input.text.strip()
        if not text:
            return

        sent = self.controller.send_message(text)
        if sent:
            self._text_input.text = ""
        else:
            # Show "not connected" feedback briefly
            self._text_input.hint_text = "Not connected — message queued"
            Clock.schedule_once(
                lambda dt: setattr(self._text_input, "hint_text", "Type a message..."),
                3
            )

    def _scroll_to_bottom(self) -> None:
        if hasattr(self, "_scroll_view"):
            self._scroll_view.scroll_y = 0

    def _exit_to_calculator(self, *args) -> None:
        app = App.get_running_app()
        if app:
            app.switch_to_calculator()
