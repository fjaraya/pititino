import os
from pathlib import Path

import pytest

from pititino.config import Settings
from pititino.tui.app import PititinoApp
from pititino.tui.workspace_tree import SORT_MODES, WorkspaceTree, sort_entries


def test_sort_entries_supports_name_and_modification_orders(tmp_path: Path) -> None:
    directory = tmp_path / "folder"
    directory.mkdir()
    alpha = tmp_path / "alpha.txt"
    zulu = tmp_path / "zulu.txt"
    alpha.write_text("alpha", encoding="utf-8")
    zulu.write_text("zulu", encoding="utf-8")
    os.utime(alpha, (100, 100))
    os.utime(directory, (200, 200))
    os.utime(zulu, (300, 300))
    entries = [zulu, directory, alpha]

    assert [path.name for path in sort_entries(entries, "name_asc")] == [
        "alpha.txt",
        "folder",
        "zulu.txt",
    ]
    assert [path.name for path in sort_entries(entries, "name_desc")] == [
        "zulu.txt",
        "folder",
        "alpha.txt",
    ]
    assert [path.name for path in sort_entries(entries, "modified_asc")] == [
        "alpha.txt",
        "folder",
        "zulu.txt",
    ]
    assert [path.name for path in sort_entries(entries, "modified_desc")] == [
        "zulu.txt",
        "folder",
        "alpha.txt",
    ]


def test_sort_entries_rejects_unknown_mode(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown sort mode"):
        sort_entries([tmp_path], "size_asc")


@pytest.mark.anyio
async def test_s_cycles_file_sort_modes(tmp_path: Path) -> None:
    app = PititinoApp(tmp_path, Settings())

    async with app.run_test() as pilot:
        await pilot.press("enter")
        tree = app.query_one("#tree", WorkspaceTree)
        assert tree.sort_mode == SORT_MODES[0]
        for expected in SORT_MODES[1:] + SORT_MODES[:1]:
            await pilot.press("s")
            assert tree.sort_mode == expected
