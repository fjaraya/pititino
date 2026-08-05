from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook


def inspect_workbook(path: str | Path) -> dict[str, Any]:
    """Return bounded workbook metadata without serializing all workbook contents."""
    workbook_path = Path(path).expanduser().resolve()
    if workbook_path.suffix.lower() != ".xlsx":
        raise ValueError("Pititino currently supports .xlsx workbooks, not legacy .xls files")
    if not workbook_path.is_file():
        raise FileNotFoundError(workbook_path)

    workbook = load_workbook(workbook_path, read_only=True, data_only=False)
    try:
        return {
            "filename": workbook_path.name,
            "path": str(workbook_path),
            "sheets": [
                {
                    "name": sheet.title,
                    "rows": sheet.max_row,
                    "columns": sheet.max_column,
                }
                for sheet in workbook.worksheets
            ],
        }
    finally:
        workbook.close()
