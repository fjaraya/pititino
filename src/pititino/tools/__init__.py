from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pititino.config import Settings
from pititino.tools import backup, csv, excel, filesystem, structured, text
from pititino.tools.registry import ToolDefinition, ToolRegistry
from pititino.workspace import Workspace


def _revisioned_proposal(workspace: Workspace, handler: Callable[[Any], Any], arguments: Any) -> Any:
    change = handler(arguments)
    return change.model_copy(update={"source_revision": workspace.revision(change.target)})


def build_registry(workspace: Workspace, settings: Settings) -> ToolRegistry:
    """Build the read-only tools available to the first agent runtime."""
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="filesystem.list",
            description="List files and directories inside the workspace.",
            args_model=filesystem.ListArguments,
            mutating=False,
            handler=lambda args: filesystem.list_files(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="filesystem.stat",
            description="Return metadata for a file or directory inside the workspace.",
            args_model=filesystem.StatArguments,
            mutating=False,
            handler=lambda args: filesystem.stat_file(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="filesystem.read_text",
            description="Read a bounded UTF-8 text file from the workspace.",
            args_model=filesystem.ReadTextArguments,
            mutating=False,
            handler=lambda args: filesystem.read_text(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="backup.list",
            description="List recoverable backups managed by Pititino.",
            args_model=backup.BackupListArguments,
            mutating=False,
            handler=lambda args: backup.list_backups(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="backup.restore",
            description="Propose restoring a backup; approval is required before replacement.",
            args_model=backup.RestoreArguments,
            mutating=True,
            handler=lambda args: _revisioned_proposal(workspace, backup.propose_restore, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="csv.inspect",
            description="Inspect bounded CSV headers, sample rows, and simple value types.",
            args_model=csv.CsvArguments,
            mutating=False,
            handler=lambda args: csv.inspect(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="csv.read",
            description="Read a bounded number of rows from a CSV file.",
            args_model=csv.CsvArguments,
            mutating=False,
            handler=lambda args: csv.read(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="text.read",
            description="Read a bounded UTF-8 text file from the workspace.",
            args_model=text.ReadTextArguments,
            mutating=False,
            handler=lambda args: text.read_text(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="text.replace",
            description="Propose replacing bounded text; approval is required before writing.",
            args_model=text.ReplaceArguments,
            mutating=True,
            handler=lambda args: _revisioned_proposal(workspace, text.propose_replace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="text.append",
            description="Propose appending text; approval is required before writing.",
            args_model=text.AppendArguments,
            mutating=True,
            handler=lambda args: _revisioned_proposal(workspace, text.propose_append, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="json.read",
            description="Parse a bounded JSON document from the workspace.",
            args_model=structured.StructuredReadArguments,
            mutating=False,
            handler=lambda args: structured.read_json(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="json.set",
            description="Propose setting a dotted JSON object path; approval is required.",
            args_model=structured.StructuredSetArguments,
            mutating=True,
            handler=lambda args: _revisioned_proposal(
                workspace, lambda value: structured.propose_set(value, "json"), args
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="yaml.read",
            description="Parse a bounded YAML document from the workspace.",
            args_model=structured.StructuredReadArguments,
            mutating=False,
            handler=lambda args: structured.read_yaml(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="yaml.set",
            description="Propose setting a dotted YAML object path; approval is required.",
            args_model=structured.StructuredSetArguments,
            mutating=True,
            handler=lambda args: _revisioned_proposal(
                workspace, lambda value: structured.propose_set(value, "yaml"), args
            ),
        )
    )
    registry.register(
        ToolDefinition(
            name="csv.write",
            description="Propose appending CSV rows; approval is required before writing.",
            args_model=csv.CsvWriteArguments,
            mutating=True,
            handler=lambda args: _revisioned_proposal(workspace, csv.propose_write, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="excel.inspect_workbook",
            description="Inspect XLSX sheet names, dimensions, and visibility.",
            args_model=excel.WorkbookArguments,
            mutating=False,
            handler=lambda args: excel.inspect_workbook(workspace, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="excel.inspect_sheet",
            description="Inspect bounded worksheet headers, samples, and simple types.",
            args_model=excel.SheetArguments,
            mutating=False,
            handler=lambda args: excel.inspect_sheet(workspace, args, settings.excel),
        )
    )
    registry.register(
        ToolDefinition(
            name="excel.read_range",
            description="Read an explicit bounded range from an XLSX worksheet.",
            args_model=excel.RangeArguments,
            mutating=False,
            handler=lambda args: excel.read_range(workspace, args, settings.excel),
        )
    )
    registry.register(
        ToolDefinition(
            name="excel.create_sheet",
            description="Propose creating a worksheet; approval is required before writing.",
            args_model=excel.CreateSheetArguments,
            mutating=True,
            handler=lambda args: _revisioned_proposal(workspace, excel.propose_create_sheet, args),
        )
    )
    registry.register(
        ToolDefinition(
            name="excel.write_range",
            description="Propose writing an explicit worksheet range; approval is required.",
            args_model=excel.WriteRangeArguments,
            mutating=True,
            handler=lambda args: _revisioned_proposal(workspace, excel.propose_write_range, args),
        )
    )
    return registry


__all__ = ["ToolDefinition", "ToolRegistry", "build_registry"]
