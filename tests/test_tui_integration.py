import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from pititino.config import Settings
from pititino.transactions.changeset import ChangeOperation, ChangeSet
from pititino.tui.app import PititinoApp
from pititino.tui.branding import COMPACT_HEADER, SPLASH_ART
from pititino.tui.screens import SplashScreen


class FakeRuntime:
    def __init__(self, pending_changes=None):
        self.pending_changes = pending_changes or []
        self.calls = []

    async def run(self, prompt, *, selected_file=None, on_text_delta=None):
        self.calls.append((prompt, selected_file))
        if on_text_delta:
            on_text_delta("streamed response")
        return "streamed response"


class FailingRuntime(FakeRuntime):
    async def run(self, prompt, *, selected_file=None, on_text_delta=None):
        raise RuntimeError("simulated worker failure")


class HangingRuntime(FakeRuntime):
    async def run(self, prompt, *, selected_file=None, on_text_delta=None):
        await asyncio.Event().wait()


def test_branding_contains_requested_identity() -> None:
    assert "PITITINO" in SPLASH_ART
    assert "AI file workbench" in SPLASH_ART
    assert COMPACT_HEADER == "  /\\_/\\   PITITINO\n( o.o )  AI file workbench\n > ^ <"
    assert PititinoApp.ALLOW_SELECT is True
    assert any(binding[0] == "super+c" for binding in PititinoApp.BINDINGS)


@pytest.mark.anyio
async def test_splash_shows_on_every_app_launch_and_skips_on_key(tmp_path) -> None:
    app = PititinoApp(Path(tmp_path), Settings())

    async with app.run_test() as pilot:
        assert isinstance(app.screen, SplashScreen)
        await pilot.press("space")
        await pilot.pause()
        assert not isinstance(app.screen, SplashScreen)


@pytest.mark.anyio
async def test_tui_selects_file_and_submits_prompt(tmp_path) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("notes", encoding="utf-8")
    app = PititinoApp(Path(tmp_path), Settings())
    runtime = FakeRuntime()
    app.runtime = runtime

    async with app.run_test() as pilot:
        await pilot.press("enter")
        app.on_workspace_tree_file_selected(SimpleNamespace(path=file_path))
        await pilot.click("#prompt")
        await pilot.press(*"summarize")
        await pilot.press("enter")
        await pilot.pause(0.2)

        assert app.selected_file == "notes.md"
        assert runtime.calls == [("summarize", "notes.md")]
        assert app.busy is False
        assert app.streamed_text == ""


@pytest.mark.anyio
async def test_tui_confirmation_applies_pending_change(tmp_path) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("old", encoding="utf-8")
    change = ChangeSet(
        target="notes.md",
        summary="Replace note",
        operations=[
            ChangeOperation(
                operation="text_replace",
                description="Replace old with new",
                arguments={"file": "notes.md", "old": "old", "new": "new", "count": 1},
            )
        ],
    )
    app = PititinoApp(Path(tmp_path), Settings(), selected_file=file_path)
    app.runtime = FakeRuntime([change])

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.click("#prompt")
        await pilot.press(*"change it")
        await pilot.press("enter")
        await pilot.pause()
        assert app.confirming_apply is True
        assert app.plan_state == "awaiting approval"

        await pilot.press(*"yes")
        await pilot.press("enter")
        await pilot.pause()

        assert file_path.read_text(encoding="utf-8") == "new"
        assert app.runtime.pending_changes == []
        assert app.plan_state == "applied"


@pytest.mark.anyio
async def test_tui_surfaces_unexpected_worker_errors(tmp_path) -> None:
    app = PititinoApp(Path(tmp_path), Settings())
    app.runtime = FailingRuntime()

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.click("#prompt")
        await pilot.press(*"fail")
        await pilot.press("enter")
        await pilot.pause(0.1)

        assert app.busy is False
        assert "state: error" in app._status_text("error")


@pytest.mark.anyio
async def test_tui_escape_cancels_active_request(tmp_path) -> None:
    app = PititinoApp(Path(tmp_path), Settings())
    app.runtime = HangingRuntime()

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.click("#prompt")
        await pilot.press(*"wait")
        await pilot.press("enter")
        await pilot.pause(0.05)
        await pilot.press("escape")
        await pilot.pause(0.05)

        assert app.busy is False
        assert "state: cancelled" in app._status_text("cancelled")


@pytest.mark.anyio
async def test_tui_c_key_cancels_pending_plan(tmp_path) -> None:
    app = PititinoApp(Path(tmp_path), Settings())
    app.confirming_apply = True
    app.runtime.pending_changes = [
        ChangeSet(
            target="notes.md",
            summary="Change note",
            operations=[
                ChangeOperation(
                    operation="text_append",
                    description="Append note",
                    arguments={"file": "notes.md", "content": "x"},
                )
            ],
        )
    ]

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        assert app.confirming_apply is False
        assert app.runtime.pending_changes == []


@pytest.mark.anyio
async def test_tui_applies_without_prompt_when_confirmation_disabled(tmp_path) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("old", encoding="utf-8")
    settings = Settings(security={"confirm_writes": False})
    change = ChangeSet(
        target="notes.md",
        summary="Replace note",
        operations=[
            ChangeOperation(
                operation="text_replace",
                description="Replace old with new",
                arguments={"file": "notes.md", "old": "old", "new": "new", "count": 1},
            )
        ],
    )
    app = PititinoApp(Path(tmp_path), settings, selected_file=file_path)
    app.runtime = FakeRuntime([change])

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.click("#prompt")
        await pilot.press(*"change")
        await pilot.press("enter")
        await pilot.pause(0.2)

        assert file_path.read_text(encoding="utf-8") == "new"
        assert app.confirming_apply is False
