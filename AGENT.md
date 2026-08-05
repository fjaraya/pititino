# AGENT.md

This file defines the working rules for AI coding agents contributing to **Pititino**.

Pititino is a terminal-native AI file workbench. It combines a Textual-based TUI, an OpenAI-compatible model endpoint, and controlled local file adapters so users can ask an AI to inspect and modify files without giving the model unrestricted shell or Python execution.

The repository is public and licensed under the Apache License 2.0.

## Primary Goal

Build Pititino as a safe, extensible, local-first AI file manipulation tool.

The intended user experience is:

1. Start `pititino` in a directory or against a specific file.
2. Navigate files from the TUI.
3. Ask the model to inspect, explain, summarize, or modify selected files.
4. Let the agent call explicit typed tools.
5. Show a change plan for write operations.
6. Require confirmation when configured.
7. Apply changes through deterministic local adapters.
8. Preserve recoverability through backups and transactional writes.

Do not turn Pititino into a generic shell agent.

## Core Design Principles

### 1. The model decides intent; local tools perform operations

The LLM should never be trusted to directly manipulate the filesystem.

Bad:

```text
Model generates arbitrary Python or shell code
        ↓
Pititino executes it
```

Good:

```text
Model requests a typed operation
        ↓
Pititino validates arguments
        ↓
Pititino executes a deterministic local adapter
```

Examples:

```text
excel.inspect_workbook
excel.inspect_sheet
excel.read_range
excel.create_sheet
excel.write_table
filesystem.read_text
json.set
yaml.set
```

### 2. Treat model output as untrusted input

Every model-generated tool call must be validated before execution.

Never assume:

- a path is safe;
- a tool exists;
- an argument has the expected type;
- a write operation is appropriate;
- a requested range or file is within configured limits.

### 3. Keep file access inside the workspace

All paths must be resolved relative to the configured workspace.

By default:

```text
allow_parent_access = false
```

Reject path traversal outside the workspace unless the user has explicitly enabled broader access.

### 4. No arbitrary shell execution by default

The default architecture must not expose:

```text
shell.exec
python.exec
subprocess.run
eval
exec
```

Do not add general-purpose command execution as a shortcut for implementing file adapters.

If a future feature genuinely requires an external command, it must be introduced as a narrowly scoped adapter with explicit arguments and validation.

### 5. Inspect incrementally

Do not send entire large files to the model.

Prefer hierarchical inspection.

For XLSX:

```text
inspect_workbook
    ↓
inspect_sheet
    ↓
read_range only when needed
```

The same idea should apply to future DOCX, PPTX, PDF, and other adapters.

### 6. Writes should be previewable and recoverable

The preferred write lifecycle is:

```text
user request
    ↓
inspection
    ↓
proposed change set
    ↓
preview
    ↓
approval
    ↓
temporary output
    ↓
validation
    ↓
backup
    ↓
atomic replacement
```

Avoid modifying the original file in place when a safer transactional path is available.

## Current Scope

Initial file formats:

- `.xlsx`
- `.csv`
- `.txt`
- `.md`
- `.json`
- `.yaml`
- `.yml`

Initial spreadsheet support targets **XLSX**, not legacy `.xls`.

Do not imply `.xls` support unless a dedicated adapter is implemented and tested.

## Technology Choices

Preferred stack:

- Python 3.11+
- Textual for the TUI
- Pydantic for typed configuration and tool schemas
- OpenAI Python SDK for OpenAI-compatible endpoints
- `openpyxl` for XLSX
- Python standard library where practical
- `uv` for dependency and environment management
- `pytest` for tests
- `ruff` for linting and formatting

Avoid unnecessary frameworks.

Keep the runtime understandable and dependency-light.

## Repository Structure

Target structure:

```text
pititino/
├── pyproject.toml
├── README.md
├── AGENT.md
├── LICENSE
├── src/
│   └── pititino/
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       │
│       ├── tui/
│       │   ├── app.py
│       │   ├── screens/
│       │   └── widgets/
│       │
│       ├── agent/
│       │   ├── runtime.py
│       │   ├── conversation.py
│       │   ├── prompts.py
│       │   └── protocol.py
│       │
│       ├── llm/
│       │   └── openai.py
│       │
│       ├── tools/
│       │   ├── registry.py
│       │   ├── filesystem.py
│       │   ├── excel.py
│       │   ├── csv.py
│       │   ├── text.py
│       │   ├── json.py
│       │   └── yaml.py
│       │
│       └── transactions/
│           ├── backup.py
│           ├── changeset.py
│           └── executor.py
│
└── tests/
```

Do not force this layout rigidly if a clearer structure emerges, but preserve separation between:

- UI;
- agent orchestration;
- LLM client;
- tool contracts;
- file adapters;
- transaction/write safety.

## Configuration

Default user configuration path:

```text
~/.config/pititino/config.toml
```

Expected shape:

```toml
[model]
base_url = "https://api.example.com/v1"
model = "example-model"
api_key_env = "PITITINO_API_KEY"
tool_calling = "auto"
temperature = 0.2
max_output_tokens = 8192

[workspace]
root = "."
allow_parent_access = false

[security]
confirm_writes = true
confirm_deletes = true
create_backups = true
allow_shell = false

[excel]
max_rows_per_read = 500
max_cells_per_read = 10000
```

Secrets must come from environment variables.

Do not store API keys in repository configuration examples.

## OpenAI-Compatible Endpoint Support

Pititino must not assume every OpenAI-compatible endpoint behaves identically.

Support three logical tool-calling modes:

```text
native
json
auto
```

### native

Use OpenAI-compatible tool/function calling.

### json

Use schema-constrained JSON actions when native tool calling is unavailable or unreliable.

Example:

```json
{
  "action": "excel.inspect_sheet",
  "arguments": {
    "file": "sales.xlsx",
    "sheet": "Revenue"
  }
}
```

### auto

Choose the best supported behavior for the configured endpoint/model.

Keep endpoint-specific logic isolated in the LLM layer.

Do not spread provider quirks throughout the application.

## Tool Registry Rules

Each tool must have:

- a stable name;
- a clear description;
- a typed argument schema;
- an explicit return structure;
- a classification as read-only or mutating;
- validation before execution.

Example concept:

```python
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]
    mutating: bool
```

Prefer explicit tool names such as:

```text
excel.inspect_workbook
excel.inspect_sheet
excel.read_range
excel.create_sheet
excel.write_range
excel.write_table
```

Avoid vague names such as:

```text
excel.do
file.run
document.execute
```

## File Adapter Rules

Each file type should be isolated behind an adapter or equivalent abstraction.

A useful shape is:

```python
class FileAdapter(Protocol):
    extensions: set[str]

    def inspect(...):
        ...

    def validate(...):
        ...

    def apply(...):
        ...
```

Adapters should own format-specific behavior.

The agent runtime should not contain `openpyxl`, CSV parsing, YAML mutation, or similar format logic.

## XLSX Rules

Use `openpyxl`.

Initial capabilities may include:

- workbook inspection;
- worksheet inspection;
- bounded range reads;
- worksheet creation;
- cell/range writes;
- table writes;
- formulas;
- basic formatting;
- freeze panes;
- column width adjustments.

Do not blindly load huge worksheets into model context.

Inspection responses should prefer:

- sheet names;
- dimensions;
- headers;
- representative rows;
- inferred column types;
- aggregate statistics;
- bounded samples.

Be careful with:

- formulas;
- merged cells;
- hidden worksheets;
- named ranges;
- workbook macros;
- external links.

Do not claim preservation of workbook features unless verified by tests.

For macro-enabled workbooks, explicit handling is required before support is advertised.

## TUI Rules

The TUI should remain keyboard-friendly and responsive.

Primary areas:

```text
filesystem browser
chat
change plan / operation preview
status / activity
```

Do not block the Textual event loop with:

- network requests;
- large workbook reads;
- expensive parsing;
- long write operations.

Use workers/background execution mechanisms provided by the application architecture while keeping state changes deterministic.

The TUI should clearly distinguish:

- user text;
- model text;
- tool calls;
- tool results;
- proposed writes;
- applied writes;
- failures.

## Write Safety

For mutating operations:

1. resolve and validate path;
2. ensure the file is inside the allowed workspace;
3. inspect source as needed;
4. build a `ChangeSet`;
5. show preview if confirmation is enabled;
6. create a backup if configured;
7. write to a temporary destination where feasible;
8. validate the generated artifact;
9. replace the original atomically where supported;
10. record the result.

Do not silently overwrite files when confirmation is enabled.

Delete operations must be treated as high-risk mutations.

## ChangeSet

Prefer representing proposed modifications explicitly.

Example concept:

```python
class ChangeSet(BaseModel):
    target: Path
    operations: list[ChangeOperation]
    summary: str
    requires_confirmation: bool = True
```

A `ChangeSet` should be serializable enough to:

- render in the TUI;
- audit;
- test;
- potentially replay later.

Do not use opaque callbacks as the only representation of planned modifications.

## Error Handling

Errors should be useful to the user and useful to tests.

Prefer domain errors such as:

```text
WorkspaceAccessError
UnsupportedFileTypeError
ToolValidationError
ToolExecutionError
WorkbookReadError
WorkbookWriteError
ConfigurationError
ModelEndpointError
```

Avoid catching `Exception` broadly unless converting it at an application boundary.

Never hide the original cause from logs/debug output.

## Logging

Do not log:

- API keys;
- Authorization headers;
- full secrets from files;
- unnecessary complete file contents.

Useful logs include:

- tool name;
- target path;
- operation duration;
- adapter used;
- result status;
- model endpoint host;
- model name.

## Testing

Every meaningful capability should have tests.

Minimum expectations:

### Tool registry

Test:

- registration;
- duplicate detection;
- argument validation;
- read vs write classification;
- unknown tool handling.

### Workspace security

Test:

- normal relative paths;
- absolute paths;
- `..` traversal;
- symlink escape where applicable;
- parent access configuration.

### XLSX

Create temporary workbooks in tests.

Test:

- workbook inspection;
- worksheet metadata;
- bounded reads;
- worksheet creation;
- writing;
- transactional save;
- reopening output after modification.

Do not depend on manually maintained binary fixture files when the workbook can be generated in the test.

### Configuration

Test:

- defaults;
- user TOML;
- missing environment keys;
- malformed TOML;
- invalid enum values;
- workspace resolution.

## Development Commands

Preferred commands:

```bash
uv sync --all-groups
uv run pititino
uv run pytest
uv run ruff check .
uv run ruff format .
```

Before considering a change complete:

```bash
uv run ruff check .
uv run pytest
```

If type checking is added later, include it in the required checks.

## Coding Style

Use modern Python.

Prefer:

- `pathlib.Path`;
- type hints;
- Pydantic models for external/LLM-facing structures;
- dataclasses or normal classes for simple internal state where appropriate;
- async only where concurrency or I/O benefits from it;
- small focused modules;
- explicit domain names.

Avoid:

- global mutable state;
- giant manager classes;
- implicit path handling;
- dicts with undocumented shapes;
- provider-specific behavior outside the LLM layer;
- UI code performing file mutations directly.

## Dependency Policy

Before adding a dependency, check whether:

1. the standard library already solves the problem;
2. the dependency is actively maintained;
3. it has a compatible license;
4. it materially reduces complexity;
5. it is needed at runtime rather than only for development.

Do not add heavy dependencies for trivial functionality.

## Adding a New File Type

When adding a new format:

1. define its supported extensions;
2. implement an adapter;
3. define bounded inspection behavior;
4. define typed tools;
5. classify read/write tools;
6. add safety validation;
7. add transaction handling for writes;
8. add tests;
9. update README support status.

Do not expose support in the README before basic implementation and tests exist.

## Adding a New Tool

For every new tool:

1. choose a precise namespace and name;
2. create a typed input schema;
3. define a structured output;
4. mark whether it mutates state;
5. validate workspace/path constraints;
6. register it centrally;
7. add tests;
8. document it if user-facing.

A tool should perform one understandable operation.

Avoid general-purpose “execute arbitrary operation” tools.

## Agent Runtime Behavior

The runtime should:

1. receive the user request;
2. identify currently selected files/workspace context;
3. provide only useful context to the model;
4. process tool calls;
5. validate them;
6. execute read-only calls automatically where allowed;
7. accumulate write requests into a change plan;
8. request user confirmation when configured;
9. execute approved changes;
10. return a concise final result.

Do not repeatedly send all prior tool results if they are no longer useful.

Context management should become an explicit subsystem as the project grows.

## Prompting Rules

System prompts should reinforce:

- use tools instead of inventing file contents;
- inspect before modifying;
- never claim a write succeeded until the tool reports success;
- never invent sheets, columns, rows, or values;
- request bounded data when possible;
- do not ask for shell execution;
- produce concise plans before mutations.

Prompts should not encode business logic that belongs in Python.

## User Confirmation

Read-only operations can generally execute without confirmation.

Mutating operations should honor:

```toml
confirm_writes = true
confirm_deletes = true
```

The confirmation UI should show enough detail for a user to understand what will change.

Do not reduce confirmation to an opaque message like:

```text
The AI wants to modify the file. Continue?
```

Prefer:

```text
sales.xlsx

+ Create worksheet "Overview"
+ Write Overview!A1:F12
+ Apply header formatting
```

## Backups

When enabled:

```toml
create_backups = true
```

store backups under a Pititino-managed location such as:

```text
.pititino/backups/
```

Backups should have collision-safe names.

Do not commit `.pititino/` runtime data.

## Git Practices

Keep commits focused.

Prefer conventional-style messages such as:

```text
feat: add workbook inspection tool
fix: reject paths outside workspace
test: cover xlsx transactional writes
docs: document JSON tool calling mode
refactor: isolate model endpoint client
```

Do not commit:

- API keys;
- generated `.pititino` runtime state;
- local virtual environments;
- temporary workbook outputs;
- editor-specific state.

## Documentation

Update `README.md` when changing:

- supported formats;
- configuration;
- CLI usage;
- installation;
- major user-facing behavior.

Update `AGENT.md` when changing:

- architecture;
- development rules;
- safety boundaries;
- contributor expectations.

Keep documentation consistent with actual implementation.

## License

All contributions must be compatible with the repository's Apache License 2.0.

New source files may use the standard Apache 2.0 SPDX identifier where appropriate:

```text
SPDX-License-Identifier: Apache-2.0
```

Do not introduce code with incompatible licensing.

## Definition of Done

A change is complete when:

- the implementation is coherent with Pititino's architecture;
- unsafe arbitrary execution has not been introduced;
- path and tool inputs are validated;
- tests cover the new behavior;
- existing tests pass;
- linting passes;
- documentation is updated when required;
- user-facing claims match actual capabilities.

When forced to choose between speed and preserving these boundaries, preserve the boundaries.
