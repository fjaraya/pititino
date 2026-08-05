from __future__ import annotations

import hashlib
from pathlib import Path

from pititino.errors import WorkspaceAccessError
from pititino.transactions.changeset import FileRevision


class Workspace:
    """Resolve user and model paths while enforcing workspace boundaries."""

    def __init__(self, root: str | Path, *, allow_parent_access: bool = False) -> None:
        requested_root = Path(root).expanduser()
        resolved_root = requested_root.resolve()
        if not resolved_root.is_dir():
            raise WorkspaceAccessError(f"Workspace does not exist or is not a directory: {resolved_root}")
        self.root = resolved_root
        self.allow_parent_access = allow_parent_access

    def resolve(self, path: str | Path = ".", *, must_exist: bool = False) -> Path:
        candidate = Path(path).expanduser()
        resolved = (candidate if candidate.is_absolute() else self.root / candidate).resolve()

        if not self.allow_parent_access and not self._inside(resolved):
            raise WorkspaceAccessError(f"Path is outside the workspace: {path}")
        if must_exist and not resolved.exists():
            raise FileNotFoundError(resolved)
        return resolved

    def _inside(self, path: Path) -> bool:
        try:
            path.relative_to(self.root)
        except ValueError:
            return False
        return True

    def revision(self, path: str | Path) -> FileRevision:
        resolved = self.resolve(path, must_exist=True)
        info = resolved.stat()
        digest: str | None = None
        if info.st_size <= 5 * 1024 * 1024 and resolved.is_file():
            hasher = hashlib.sha256()
            with resolved.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    hasher.update(chunk)
            digest = hasher.hexdigest()
        return FileRevision(size=info.st_size, mtime_ns=info.st_mtime_ns, sha256=digest)
