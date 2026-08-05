import pytest

from pititino.errors import WorkspaceAccessError
from pititino.workspace import Workspace


def test_workspace_resolves_relative_and_absolute_paths(tmp_path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello", encoding="utf-8")
    workspace = Workspace(tmp_path)

    assert workspace.resolve("notes.txt") == file_path
    assert workspace.resolve(file_path) == file_path


def test_workspace_rejects_parent_traversal(tmp_path) -> None:
    root = tmp_path / "inside"
    root.mkdir()
    workspace = Workspace(root)

    with pytest.raises(WorkspaceAccessError):
        workspace.resolve("../outside.txt")


def test_workspace_rejects_symlink_escape(tmp_path) -> None:
    root = tmp_path / "inside"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    workspace = Workspace(root)

    with pytest.raises(WorkspaceAccessError):
        workspace.resolve("link/file.txt")


def test_workspace_can_explicitly_allow_parent_access(tmp_path) -> None:
    root = tmp_path / "inside"
    root.mkdir()
    workspace = Workspace(root, allow_parent_access=True)

    assert workspace.resolve("../outside.txt") == tmp_path / "outside.txt"
