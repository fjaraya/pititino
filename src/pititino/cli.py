from __future__ import annotations

import argparse
from pathlib import Path

from pititino.config import load_settings
from pititino.errors import ConfigurationError
from pititino.tui.app import PititinoApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pititino",
        description="Terminal-native AI file workbench.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Workspace directory or file to focus on (default: current directory)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        raise SystemExit(str(exc)) from exc

    requested = Path(args.path or settings.workspace.root).expanduser().resolve()
    workspace = requested.parent if requested.is_file() else requested
    if not workspace.is_dir():
        raise SystemExit(f"Workspace does not exist or is not a directory: {workspace}")

    selected_file = requested if requested.is_file() else None
    PititinoApp(workspace=workspace, settings=settings, selected_file=selected_file).run()
