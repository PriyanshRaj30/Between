"""
Texie — Private Calculator-Based Messaging App
Main entry point for Kivy mobile application.
"""
import os
import sys

# Ensure proper imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, NoTransition, FadeTransition
from kivy.core.window import Window
from kivy.utils import platform

# Import screens
from mobile.calculator.calculator_ui import CalculatorScreen
from mobile.private_chat.chat_ui import PrivateChatScreen

# Set window size for development (mobile-like)
if platform not in ("android", "ios"):
    Window.size = (360, 720)
    Window.minimum_width = 320
    Window.minimum_height = 600


class TexieApp(App):
    """
    Main Texie application.

    State machine:
      CALCULATOR  →(secret sequence)→  PRIVATE_CHAT
      PRIVATE_CHAT  →(exit)→  CALCULATOR
    """

    title = "Calculator"   # Appears as a normal calculator in recents

    def build(self):
        self.sm = ScreenManager(transition=FadeTransition(duration=0.25))

        # Add screens
        self.sm.add_widget(CalculatorScreen(name="calculator"))
        self.sm.add_widget(PrivateChatScreen(name="private_chat"))

        # Start in calculator mode
        self.sm.current = "calculator"

        return self.sm

    def switch_to_private(self):
        """Called by CalculatorScreen when secret sequence is entered."""
        self.sm.transition = FadeTransition(duration=0.3)
        self.sm.current = "private_chat"

    def switch_to_calculator(self):
        """Called by PrivateChatScreen when user exits."""
        self.sm.transition = FadeTransition(duration=0.2)
        self.sm.current = "calculator"


def main():
    TexieApp().run()


if __name__ == "__main__":
    main()
