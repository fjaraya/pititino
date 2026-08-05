from __future__ import annotations

import asyncio
from collections import defaultdict
from pathlib import Path
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Input, RichLog, Static
from textual.worker import Worker

from pititino.agent.runtime import AgentRuntime
from pititino.config import Settings
from pititino.errors import PititinoError
from pititino.llm.openai import OpenAIChatClient
from pititino.tools import build_registry
from pititino.transactions.changeset import ChangeSet
from pititino.transactions.executor import apply_changeset
from pititino.tui.branding import COMPACT_HEADER
from pititino.tui.screens import SplashScreen
from pititino.tui.workspace_tree import WorkspaceTree
from pititino.workspace import Workspace


class PititinoApp(App[None]):
    """Initial Pititino TUI shell."""

    TITLE = "Pititino"
    SUB_TITLE = "AI file workbench"
    ALLOW_SELECT = True
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("a", "apply_changes", "Apply proposed changes"),
        ("c", "cancel_changes", "Cancel proposed changes"),
        ("escape", "cancel_request", "Cancel request"),
        ("s", "cycle_sort", "Cycle file sort"),
        ("super+c", "copy_selected_text", "Copy selected text"),
        ("ctrl+shift+r", "reset_conversation", "Reset conversation"),
    ]

    CSS = """
    #workspace { height: 1fr; }
    #brand { height: 3; padding: 0 1; color: $text; }
    #browser { width: 34%; border-right: solid $primary; }
    #main { width: 66%; }
    #chat { height: 1fr; padding: 1 2; border: solid $surface; }
    #response-stream { height: auto; padding: 0 2; color: $text; }
    #plan { display: none; height: auto; max-height: 14; padding: 1 2; border: solid $warning; }
    #plan-actions { height: auto; margin-top: 1; }
    #plan-actions Button { margin-right: 1; }
    #selection { height: auto; padding: 0 1; color: $text-muted; }
    #status { height: auto; padding: 0 1; color: $text-muted; }
    #prompt { dock: bottom; }
    """

    def __init__(self, workspace: Path, settings: Settings, selected_file: Path | None = None) -> None:
        super().__init__()
        self.workspace = workspace
        self.settings = settings
        self.safe_workspace = Workspace(
            workspace, allow_parent_access=settings.workspace.allow_parent_access
        )
        self.selected_file: str | None = (
            str(selected_file.relative_to(workspace)) if selected_file is not None else None
        )
        self.confirming_apply = False
        self.streamed_response = False
        self.streamed_text = ""
        self.busy = False
        self.applying = False
        self.prompt_worker: Worker[None] | None = None
        self.apply_worker: Worker[None] | None = None
        self.plan_state = "none"
        self.runtime = AgentRuntime(
            settings,
            build_registry(self.safe_workspace, settings),
            OpenAIChatClient(settings.model),
            on_tool_activity=self._show_activity,
        )
        self.chat_lines = ["# Pititino", "Select a file and ask a question."]

    def compose(self) -> ComposeResult:
        yield Static(COMPACT_HEADER, id="brand")
        with Horizontal(id="workspace"):
            with Vertical(id="browser"):
                yield Static(f"Workspace: {self.workspace}")
                yield Static("Sort: name (asc)", id="browser-sort")
                yield WorkspaceTree(self.workspace, id="tree")
            with Vertical(id="main"):
                yield RichLog(markup=True, wrap=True, id="chat")
                yield Static(id="response-stream")
                with Vertical(id="plan"):
                    yield Static("", id="plan-details")
                    with Horizontal(id="plan-actions"):
                        yield Button("Apply", id="apply-plan", variant="success")
                        yield Button("Cancel", id="cancel-plan", variant="error")
                yield Static(self._selection_label(), id="selection")
                yield Static(self._status_text(), id="status")
                yield Input(placeholder="Ask Pititino to inspect or modify a file…", id="prompt")
        yield Footer()

    def on_workspace_tree_file_selected(self, event: WorkspaceTree.FileSelected) -> None:
        path = event.path
        self.selected_file = str(path.relative_to(self.workspace))
        self.query_one("#selection", Static).update(f"Selected: {self.selected_file}")
        self.query_one("#status", Static).update(self._status_text())

    def on_mount(self) -> None:
        chat = self.query_one("#chat", RichLog)
        for line in self.chat_lines:
            chat.write(line)
        self.push_screen(SplashScreen())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return
        event.input.value = ""
        if self.busy or self.applying:
            self._write_chat("**Pititino:** A request is already running. Press Escape to cancel it.")
            return
        if self.confirming_apply:
            self.confirming_apply = False
            if prompt.lower() == "yes":
                self._approve_pending_changes()
            else:
                self.runtime.pending_changes.clear()
                self._write_chat("**Pititino:** Changes cancelled.")
            return
        self._write_chat(f"**You:** {prompt}")
        self.prompt_worker = self.run_prompt(prompt)

    @work(exclusive=True)
    async def run_prompt(self, prompt: str) -> None:
        self.busy = True
        self.query_one("#selection", Static).update("Working...")
        self.query_one("#status", Static).update(self._status_text("working"))
        self.streamed_response = False
        self.streamed_text = ""
        self.query_one("#response-stream", Static).update("")
        try:
            response = await self.runtime.run(
                prompt,
                selected_file=self.selected_file,
                on_text_delta=self._show_text_delta,
            )
            if self.streamed_response:
                self._write_chat(f"**Pititino:** {response}")
                self.query_one("#response-stream", Static).update("")
            else:
                self._write_chat(f"**Pititino:** {response}")
            if self.runtime.pending_changes:
                plan = self._pending_plan_text()
                self._show_plan(plan, "awaiting approval" if self.settings.security.confirm_writes else "applying")
                if self.settings.security.confirm_writes:
                    self._write_chat(
                        f"**Proposed changes:**\n{plan}\n"
                        "Type `yes` to apply or anything else to cancel."
                    )
                    self.confirming_apply = True
                else:
                    self._write_chat(f"**Applying approved changes:**\n{plan}")
                    self.applying = True
                    self.apply_worker = self.apply_pending_changes()
            self.query_one("#selection", Static).update(self._selection_label())
            if not self.applying:
                self.query_one("#status", Static).update(self._status_text("ready"))
        except PititinoError as exc:
            self._write_chat(f"**Error:** {exc}")
            self.query_one("#selection", Static).update(self._selection_label())
            self.query_one("#status", Static).update(self._status_text("error"))
        except asyncio.CancelledError:
            self.query_one("#response-stream", Static).update("")
            self._write_chat("**Pititino:** Request cancelled.")
            self.query_one("#selection", Static).update(self._selection_label())
            self.query_one("#status", Static).update(self._status_text("cancelled"))
        except Exception as exc:  # noqa: BLE001 - surface worker failures in the TUI
            self._write_chat(f"**Unexpected error:** {exc}")
            self.query_one("#selection", Static).update(self._selection_label())
            self.query_one("#status", Static).update(self._status_text("error"))
        finally:
            self.busy = False
            self.prompt_worker = None
            self.streamed_text = ""
            self.query_one("#response-stream", Static).update("")

    def _write_chat(self, text: str) -> None:
        self.query_one("#chat", RichLog).write(text)

    def _show_activity(self, text: str) -> None:
        self.query_one("#chat", RichLog).write(f"`{text}`")

    def _show_text_delta(self, text: str) -> None:
        self.streamed_response = True
        stream = self.query_one("#response-stream", Static)
        self.streamed_text += text
        stream.update(self.streamed_text)

    def _selection_label(self) -> str:
        return f"Selected: {self.selected_file}" if self.selected_file else "No file selected"

    def _status_text(self, state: str = "ready") -> str:
        selected = self.selected_file or "none"
        return (
            f"workspace: {self.workspace} | file: {selected} | model: {self.settings.model.model} "
            f"| tools: {self.settings.model.tool_calling} | state: {state}"
        )

    def action_apply_changes(self) -> None:
        if self.busy or self.applying:
            self._write_chat("**Pititino:** Wait for the current request to finish.")
            return
        if self.runtime.pending_changes:
            self._approve_pending_changes()
        else:
            self._write_chat("No proposed changes are waiting for approval.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-plan":
            self._approve_pending_changes()
        elif event.button.id == "cancel-plan":
            self._cancel_pending_changes()

    def action_cycle_sort(self) -> None:
        tree = self.query_one("#tree", WorkspaceTree)
        tree.cycle_sort()
        self.query_one("#browser-sort", Static).update(f"Sort: {tree.sort_label}")

    def action_copy_selected_text(self) -> None:
        selection = self.screen.get_selected_text()
        if selection:
            self.copy_to_clipboard(selection)

    def action_reset_conversation(self) -> None:
        if self.busy or self.applying:
            self._write_chat("**Pititino:** Wait for the current request to finish.")
            return
        self.runtime.reset_conversation()
        self._write_chat("**Pititino:** Conversation context reset.")

    @work(exclusive=True)
    async def apply_pending_changes(self) -> None:
        self.applying = True
        self.query_one("#status", Static).update(self._status_text("applying"))
        try:
            changes = self._group_pending_changes()
            for change in changes:
                try:
                    result = apply_changeset(change, self.safe_workspace, self.settings)
                    self.runtime.pending_changes = [
                        pending
                        for pending in self.runtime.pending_changes
                        if pending.target != change.target
                    ]
                    self._write_chat(f"**Applied:** {change.summary} ({result})")
                except (PititinoError, OSError) as exc:
                    self._write_chat(f"**Write failed:** {change.target}: {exc}")
                    self._show_plan(self._pending_plan_text(), "failed")
                    self.query_one("#status", Static).update(self._status_text("write failed"))
                    return
            if not self.runtime.pending_changes:
                self._hide_plan("applied")
                self.query_one("#status", Static).update(self._status_text("applied"))
            else:
                self._show_plan(self._pending_plan_text(), "partial failure")
                self._write_chat("**Some changes remain pending and can be retried.**")
                self.query_one("#status", Static).update(self._status_text("partial failure"))
        except asyncio.CancelledError:
            self._write_chat("**Pititino:** Write operation cancelled.")
            self._show_plan(self._pending_plan_text(), "cancelled")
            self.query_one("#status", Static).update(self._status_text("cancelled"))
            raise
        finally:
            self.applying = False
            self.apply_worker = None

    def action_cancel_request(self) -> None:
        if self.confirming_apply:
            self._cancel_pending_changes()
            return
        if self.prompt_worker is not None and self.busy:
            self.prompt_worker.cancel()
            return
        if self.apply_worker is not None and self.applying:
            self.apply_worker.cancel()

    def action_cancel_changes(self) -> None:
        if self.confirming_apply or self.runtime.pending_changes:
            self._cancel_pending_changes()
        else:
            self._write_chat("No proposed changes are waiting for approval.")

    def _cancel_pending_changes(self) -> None:
        self.confirming_apply = False
        self.runtime.pending_changes.clear()
        self._hide_plan("cancelled")
        self._write_chat("**Pititino:** Proposed changes cancelled.")
        self.query_one("#status", Static).update(self._status_text("cancelled"))

    def _approve_pending_changes(self) -> None:
        if self.busy or self.applying:
            self._write_chat("**Pititino:** Wait for the current request to finish.")
            return
        if not self.runtime.pending_changes:
            self._write_chat("No proposed changes are waiting for approval.")
            return
        self.confirming_apply = False
        self.applying = True
        self._show_plan(self._pending_plan_text(), "applying")
        self.apply_worker = self.apply_pending_changes()

    def _group_pending_changes(self) -> list[ChangeSet]:
        grouped: dict[str, list[ChangeSet]] = defaultdict(list)
        for change in self.runtime.pending_changes:
            grouped[change.target].append(change)
        return [
            ChangeSet(
                target=target,
                operations=[operation for change in changes for operation in change.operations],
                summary="; ".join(change.summary for change in changes),
                source_revision=changes[0].source_revision,
            )
            for target, changes in grouped.items()
        ]

    def _pending_plan_text(self) -> str:
        lines: list[str] = []
        for change in self._group_pending_changes():
            lines.append(f"**{change.target}**")
            lines.extend(f"+ {operation.description}" for operation in change.operations)
        return "\n".join(lines)

    def _show_plan(self, plan: str, state: str) -> None:
        self.plan_state = state
        self.query_one("#plan-details", Static).update(f"Change plan [{state}]\n{plan}")
        self.query_one("#plan", Vertical).styles.display = "block"

    def _hide_plan(self, state: str) -> None:
        self.plan_state = state
        self.query_one("#plan-details", Static).update(f"Change plan [{state}]")
        if state in {"applied", "cancelled"}:
            self.query_one("#plan", Vertical).styles.display = "none"
