from openpyxl import Workbook

from pititino.tools.excel import inspect_workbook


def test_inspect_workbook_lists_sheets(tmp_path) -> None:
    path = tmp_path / "sample.xlsx"
    workbook = Workbook()
    workbook.active.title = "Sales"
    workbook.create_sheet("Customers")
    workbook.save(path)

    result = inspect_workbook(path)

    assert result["filename"] == "sample.xlsx"
    assert [sheet["name"] for sheet in result["sheets"]] == ["Sales", "Customers"]
