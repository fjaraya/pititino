from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from textual.message import Message
from textual.widgets import Tree

SORT_MODES: tuple[str, ...] = (
    "name_asc",
    "name_desc",
    "modified_asc",
    "modified_desc",
)

SORT_LABELS = {
    "name_asc": "name (asc)",
    "name_desc": "name (desc)",
    "modified_asc": "modified (asc)",
    "modified_desc": "modified (desc)",
}


def sort_entries(entries: list[Path], mode: str) -> list[Path]:
    """Sort directory entries while keeping directories before files."""
    if mode not in SORT_MODES:
        raise ValueError(f"Unknown sort mode: {mode}")

    directories = [entry for entry in entries if entry.is_dir() and not entry.is_symlink()]
    files = [entry for entry in entries if entry not in directories]
    grouped = [directories, files]
    reverse = mode.endswith("desc")

    for entries_group in grouped:
        if mode.startswith("name"):
            entries_group.sort(key=lambda entry: entry.name.casefold(), reverse=reverse)
        else:
            entries_group.sort(
                key=lambda entry: (entry.stat().st_mtime_ns, entry.name.casefold()),
                reverse=reverse,
            )
    return directories + files


class WorkspaceTree(Tree[Path]):
    """Lazy, workspace-rooted file tree with user-selectable sorting."""

    class FileSelected(Message):
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = []

    def __init__(self, workspace: Path, *, sort_mode: str = "name_asc", **kwargs: Any) -> None:
        super().__init__(workspace.name or str(workspace), data=workspace, **kwargs)
        self.workspace = workspace
        self.sort_mode = sort_mode

    def on_mount(self) -> None:
        self.root.expand()
        self._populate(self.root, replace=True)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[Path]) -> None:
        self._populate(event.node)

    def on_tree_node_selected(self, event: Tree.NodeSelected[Path]) -> None:
        path = event.node.data
        if path is not None and path.is_file():
            self.post_message(self.FileSelected(path))

    def cycle_sort(self) -> str:
        index = SORT_MODES.index(self.sort_mode)
        self.sort_mode = SORT_MODES[(index + 1) % len(SORT_MODES)]
        self._refresh_tree()
        return self.sort_mode

    @property
    def sort_label(self) -> str:
        return SORT_LABELS[self.sort_mode]

    def _refresh_tree(self) -> None:
        expanded = self._expanded_paths(self.root)
        self._populate(self.root, replace=True)
        for path in sorted(expanded, key=lambda value: len(value.parts)):
            node = self._find_node(path)
            if node is not None:
                self._populate(node, replace=True)
                node.expand()

    def _populate(self, node: Any, *, replace: bool = False) -> None:
        path = node.data
        if path is None or not path.is_dir():
            return
        if node.children and not replace:
            return
        if replace:
            node.remove_children()
        try:
            entries = sort_entries(list(path.iterdir()), self.sort_mode)
        except OSError:
            return
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                node.add(entry.name, entry, allow_expand=True)
            else:
                node.add_leaf(entry.name, entry)

    def _expanded_paths(self, node: Any) -> set[Path]:
        expanded: set[Path] = set()
        for child in node.children:
            if child.is_expanded and child.data is not None:
                expanded.add(child.data)
                expanded.update(self._expanded_paths(child))
        return expanded

    def _find_node(self, path: Path) -> Any | None:
        if self.root.data == path:
            return self.root
        return self._find_node_in(self.root, path)

    def _find_node_in(self, node: Any, path: Path) -> Any | None:
        for child in node.children:
            if child.data == path:
                return child
            result = self._find_node_in(child, path)
            if result is not None:
                return result
        return None
