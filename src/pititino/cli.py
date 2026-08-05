from __future__ import annotations

import argparse
from pathlib import Path

from pititino.config import load_settings
from pititino.tui.app import PititinoApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pititino",
        description="Terminal-native AI file workbench.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Workspace directory or file to focus on (default: current directory)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    requested = Path(args.path).expanduser().resolve()
    workspace = requested.parent if requested.is_file() else requested
    if not workspace.is_dir():
        raise SystemExit(f"Workspace does not exist or is not a directory: {workspace}")

    settings = load_settings()
    PititinoApp(workspace=workspace, settings=settings).run()
