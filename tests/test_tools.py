import pytest
from openpyxl import Workbook

from pititino.config import Settings
from pititino.errors import ToolValidationError, WorkbookReadError, WorkspaceAccessError
from pititino.tools import build_registry
from pititino.workspace import Workspace


def make_workbook(path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Revenue"
    sheet.append(["Month", "Amount"])
    sheet.append(["January", 10])
    sheet.append(["February", 20])
    hidden = workbook.create_sheet("Internal")
    hidden.sheet_state = "hidden"
    workbook.save(path)


def test_registry_validates_arguments_and_exposes_xlsx_tools(tmp_path) -> None:
    path = tmp_path / "sales.xlsx"
    make_workbook(path)
    registry = build_registry(Workspace(tmp_path), Settings())

    workbook = registry.invoke("excel.inspect_workbook", {"file": "sales.xlsx"})
    assert workbook["sheets"][1]["state"] == "hidden"

    sheet = registry.invoke("excel.inspect_sheet", {"file": "sales.xlsx", "sheet": "Revenue"})
    assert sheet["headers"] == ["Month", "Amount"]
    assert sheet["sample_rows"] == [["January", 10], ["February", 20]]

    with pytest.raises(WorkspaceAccessError):
        registry.invoke("excel.inspect_workbook", {"file": "../sales.xlsx"})


def test_read_range_is_bounded(tmp_path) -> None:
    path = tmp_path / "sales.xlsx"
    make_workbook(path)
    settings = Settings(excel={"max_rows_per_read": 1, "max_cells_per_read": 2})
    registry = build_registry(Workspace(tmp_path), settings)

    with pytest.raises(WorkbookReadError, match="max_rows_per_read"):
        registry.invoke(
            "excel.read_range",
            {"file": "sales.xlsx", "sheet": "Revenue", "range": "A1:B2"},
        )


def test_registry_rejects_unknown_tools() -> None:
    with pytest.raises(ToolValidationError, match="Unknown tool"):
        build_registry(Workspace("."), Settings()).invoke("missing.tool", {})
