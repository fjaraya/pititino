from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DirectoryTree, Footer, Header, Input, Markdown, Static

from pititino.config import Settings


class PititinoApp(App[None]):
    """Initial Pititino TUI shell."""

    TITLE = "Pititino"
    SUB_TITLE = "AI file workbench"

    CSS = """
    #workspace { height: 1fr; }
    #browser { width: 34%; border-right: solid $primary; }
    #main { width: 66%; }
    #chat { height: 1fr; padding: 1 2; }
    #selection { height: auto; padding: 0 1; color: $text-muted; }
    #prompt { dock: bottom; }
    """

    def __init__(self, workspace: Path, settings: Settings) -> None:
        super().__init__()
        self.workspace = workspace
        self.settings = settings

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="workspace"):
            with Vertical(id="browser"):
                yield Static(f"Workspace: {self.workspace}")
                yield DirectoryTree(str(self.workspace), id="tree")
            with Vertical(id="main"):
                yield Markdown(
                    "# Pititino\n\nSelect a file and describe what you want to do with it.",
                    id="chat",
                )
                yield Static("No file selected", id="selection")
                yield Input(placeholder="Ask Pititino to inspect or modify a file…", id="prompt")
        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.query_one("#selection", Static).update(f"Selected: {event.path}")
