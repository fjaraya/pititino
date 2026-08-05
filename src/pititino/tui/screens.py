from __future__ import annotations

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Static

from pititino.tui.branding import SPLASH_ART


class SplashScreen(Screen[None]):
    """Short branded launch screen; any key skips the timer."""

    CSS = """
    Screen { align: center middle; background: $surface; }
    #splash-art { width: auto; height: auto; content-align: center middle; color: $text; }
    """

    def compose(self) -> ComposeResult:
        yield Static(SPLASH_ART, id="splash-art")

    def on_mount(self) -> None:
        self.set_timer(1.2, self.dismiss_splash)

    def on_key(self, event: Key) -> None:
        event.stop()
        self.dismiss_splash()

    def dismiss_splash(self) -> None:
        if self.app.screen is self:
            self.dismiss()
