# Pititino

<p align="center">
  <img src="assets/pititino.png" alt="Pititino" width="420">
</p>

**Pititino** is a terminal-native AI file workbench.

It combines a filesystem browser, an interactive chat interface, and controlled local file operations so you can ask an OpenAI-compatible model to inspect, understand, and modify files in your workspace.

Instead of giving the model unrestricted shell or Python access, Pititino exposes a typed set of file tools. The model decides **what** should be done; Pititino performs the operation locally through deterministic adapters and can require approval before modifying anything.

> **Status:** Early development / experimental. The first usable read-only and transactional XLSX slice is implemented.

## What Pititino is for

Pititino is designed for workflows such as:

- Inspect a spreadsheet and explain its structure.
- Add a new worksheet containing an executive overview of the other sheets.
- Summarize or reorganize CSV data.
- Read and update JSON or YAML configuration files.
- Review Markdown or text files and apply requested edits.
- Navigate a local workspace from a TUI while discussing files with an AI model.
- Preview planned file modifications before applying them.
- Keep backups and an audit trail of local changes.

Example:

```text
You:
Add a new sheet named "Overview" to sales.xlsx.
Summarize the contents of all existing sheets and include useful totals.

Pititino:
I inspected sales.xlsx.

Sheets:
- Sales 2025
- Sales 2026
- Customers
- Products

Proposed changes:
+ Create worksheet "Overview"
+ Add workbook summary
+ Add per-sheet statistics
+ Add selected totals
+ Format the summary table

Apply changes? [y/N]
```

## Design principles

Pititino follows a few important rules:

1. **Files stay local by default.** Pititino reads and writes files on the machine where it runs.
2. **The model does not get arbitrary shell access.** File operations are implemented as explicit, typed tools.
3. **Large files are inspected incrementally.** Pititino does not blindly serialize an entire workbook into the model context.
4. **Writes can require approval.** The model produces a change plan before Pititino modifies a file.
5. **Writes should be recoverable.** Pititino can create backups and use temporary files before replacing originals.
6. **The LLM endpoint is replaceable.** Pititino talks to an OpenAI-compatible API and is not tied to a specific model provider.

## TUI

The initial interface is built around three main areas:

```text
┌──────────────────────┬──────────────────────────────────────────────┐
│ Files                │ Chat                                         │
│                      │                                              │
│ 📁 reports           │ You: Summarize this workbook and create      │
│   📄 sales.xlsx  ◀   │      an Overview worksheet.                  │
│   📄 notes.md        │                                              │
│ 📁 exports           │ Pititino: I inspected the workbook...        │
│                      │                                              │
│                      │ Proposed changes                             │
│                      │ + Create sheet "Overview"                    │
│                      │ + Write summary table                        │
│                      │                                              │
│                      │             [ Apply ] [ Cancel ]             │
├──────────────────────┴──────────────────────────────────────────────┤
│ sales.xlsx | XLSX | model: example-model | endpoint: configured    │
└─────────────────────────────────────────────────────────────────────┘
```

The TUI is intended to provide filesystem navigation, file selection, chat history, streaming responses, tool activity, change-plan previews, approvals, operation results, and keyboard-driven navigation.

When a write plan is waiting, click `Apply` or `Cancel`, or use `a` / `c`.
Press `Escape` to cancel an active model request or write operation.

## Architecture

```text
                           ┌──────────────────────┐
                           │     Textual TUI      │
                           │ Files │ Chat │ Plan  │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │    Agent Runtime     │
                           │ conversation         │
                           │ context management   │
                           │ tool dispatcher      │
                           └──────────┬───────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
          ┌────────────────────┐              ┌─────────────────────┐
          │ OpenAI-compatible  │              │    Tool Registry    │
          │ API                │              │ filesystem.*        │
          │ /v1/...            │              │ excel.* / csv.*    │
          └────────────────────┘              │ text.* / json.*    │
                                              │ yaml.*              │
                                              └──────────┬──────────┘
                                                         │
                                                         ▼
                                              ┌─────────────────────┐
                                              │   File Adapters     │
                                              │ openpyxl / pathlib  │
                                              │ Python stdlib       │
                                              └─────────────────────┘
```

## Supported file types

The initial target is:

| Format | Extension | Initial capabilities |
|---|---|---|
| Excel | `.xlsx` | Inspect workbooks/sheets, read ranges, create sheets, write cells/tables |
| CSV | `.csv` | Bounded inspect/read and approved row appends |
| Text | `.txt` | Bounded read and approved replace/append |
| Markdown | `.md` | Bounded read and approved replace/append |
| JSON | `.json` | Bounded read and approved dotted-path updates |
| YAML | `.yaml`, `.yml` | Bounded read and approved dotted-path updates |

### Excel note

The first Excel implementation targets **XLSX** files through `openpyxl`.

Legacy binary `.xls` files are not part of the initial scope and should not be treated as equivalent to `.xlsx`.

## Requirements

- Python 3.11 or newer.
- An OpenAI-compatible inference endpoint.
- A model capable of reliably following structured instructions.
- Native OpenAI-style tool/function calling is recommended but not required.

Pititino is intended to work with endpoints such as LiteLLM, vLLM's OpenAI-compatible server, hosted OpenAI-compatible APIs, and other compatible gateways.

Compatibility can vary between servers and models, particularly around tool calling.
If a model does not reliably select native tools, set `tool_calling = "json"` to
use the validated JSON action protocol explicitly.

## Installation

Pititino is not yet published to PyPI. During development, install it from the repository.

### Using `uv`

```bash
git clone https://github.com/fjaraya/pititino.git
cd pititino

uv sync
uv run pititino
```

### Editable development installation

```bash
git clone https://github.com/fjaraya/pititino.git
cd pititino

uv venv
source .venv/bin/activate
uv pip install -e .

pititino
```

## Configuration

Pititino reads its user configuration from:

```text
~/.config/pititino/config.toml
```

Example:

```toml
[model]
api = "chat_completions"
base_url = "https://api.example.com/v1"
model = "example-model"
api_key_env = "PITITINO_API_KEY"

# auto   = choose the best supported mode
# native = require OpenAI-style tool/function calls
# json   = use validated structured JSON actions
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

[agent]
max_tool_rounds = 20
timeout_seconds = 120
max_history_turns = 10
```

Set the API key separately:

```bash
export PITITINO_API_KEY="your-api-key"
```

Pititino also loads a local `.env` file from the launch directory without
overwriting variables already exported in the environment. Keep `.env` out of
version control.

The model layer uses Pydantic AI's Chat Completions provider to connect to any
OpenAI-compatible `/v1/chat/completions` endpoint. The configured model name is
passed through unchanged; it may refer to Qwen, Llama, Mistral, Gemma,
DeepSeek, or another model served by the gateway. The agent runtime depends on
the provider-neutral `ModelBackend` contract rather than a model vendor SDK.

For a local server that ignores API keys:

```bash
export PITITINO_API_KEY="not-used"
```

## Usage

Start Pititino in the current directory:

```bash
pititino
```

Use another directory as the workspace:

```bash
pititino ./reports
```

Open focused on a specific file:

```bash
pititino ./reports/sales.xlsx
```

During development:

```bash
uv run pititino ./reports
```

In the filesystem browser, press `s` to cycle through workspace entry sorting
modes: name ascending, name descending, modification time ascending, and
modification time descending. Files and directories are sorted together.

Chat text can be selected by dragging over it and copied with `Command-C` on
macOS. If the terminal captures mouse input first, use the terminal's native
selection modifier, typically `Option` while dragging.

The prompt keeps an in-session history. Press `Up` to recall an earlier prompt,
`Down` to move forward or restore your draft, and `Enter` to submit the recalled
prompt again.

Pititino keeps the last 10 completed conversation turns during the current
session, including when switching files. Press `Ctrl-Shift-R` to reset that
context manually.

## Example workflows

### Create an overview worksheet

Select `sales.xlsx` and ask:

```text
Add a new sheet named "Overview".

Inspect all existing worksheets and create a concise executive overview.
Include the purpose of each sheet, row counts, important totals, and any
obvious trends you can infer from the data.
```

Pititino should inspect workbook metadata first, request only the ranges or summaries it needs, and then produce a proposed change set.

### Inspect without modifying

```text
Explain the structure of this workbook and tell me what each sheet appears
to contain. Do not modify the file.
```

### Update structured configuration

Select a YAML file and ask:

```text
Add a production environment using the same structure as staging, but set
replicas to 3 and disable debug mode.
```

Pititino should present the structured modification before writing when write confirmation is enabled.

## Tool model

The model interacts with files through a controlled tool registry.

Available and planned tools include:

```text
filesystem.list
filesystem.stat
filesystem.read_text
backup.list
backup.restore
filesystem.copy
filesystem.move

excel.inspect_workbook
excel.inspect_sheet
excel.read_range
excel.create_sheet
excel.write_range
excel.write_table
excel.set_formula
excel.delete_sheet

csv.inspect
csv.read
csv.write

text.read
text.replace
text.append

json.read
json.set

yaml.read
yaml.set
```

Arbitrary shell execution is intentionally excluded from the default design.

## Large files

Pititino should avoid sending complete large files to the model.

For XLSX files, inspection is hierarchical:

```text
excel.inspect_workbook("financial-report.xlsx")
        │
        ▼
sheet names + dimensions + workbook metadata
        │
        ▼
excel.inspect_sheet("Revenue")
        │
        ▼
headers + representative samples + statistics
        │
        ▼
excel.read_range("Revenue", "A1:F100")
        │
        ▼
only if more detail is actually required
```

This keeps context bounded and reduces unnecessary data transfer.

## Tool calling compatibility

OpenAI-compatible does not guarantee identical tool-calling behavior across every endpoint and model.

Pititino supports three modes.

### Native

```toml
tool_calling = "native"
```

Uses OpenAI-compatible function/tool calls.

### Structured JSON

```toml
tool_calling = "json"
```

The model returns a constrained action such as:

```json
{
  "action": "excel.inspect_sheet",
  "arguments": {
    "file": "sales.xlsx",
    "sheet": "Revenue"
  }
}
```

Pititino validates the action before executing it.

### Auto

```toml
tool_calling = "auto"
```

Tries native tool calls first. If the endpoint rejects native tools, or the
model returns a response without selecting a tool, Pititino retries once using
the validated JSON action protocol. After a native tool call succeeds, normal
final prose is returned without an additional fallback request.

## Safe writes

The intended write workflow is:

```text
User request
     │
     ▼
Inspect files
     │
     ▼
Generate change plan
     │
     ▼
Preview
     │
     ├── Cancel
     │
     └── Apply
            │
            ▼
      Write temporary file
            │
            ▼
      Validate result
            │
            ▼
      Backup original
            │
            ▼
      Replace target
```

Runtime state may be stored under:

```text
.pititino/
├── backups/
├── history/operations.jsonl
└── tmp/
```

The history file records timestamps, target paths, operation names, statuses,
backup paths, and failure reasons. It does not record file contents or tool arguments.

## Security model

Pititino should assume model output is untrusted input.

Important constraints include:

- Tool arguments are schema validated.
- Filesystem operations remain inside the configured workspace unless explicitly permitted.
- Parent-directory traversal is rejected by default.
- Shell execution is disabled by default.
- Write and delete operations can require explicit confirmation.
- File adapters decide which operations are valid for each file type.
- Temporary output can be validated before replacing an original file.
- Approved changes are rejected if the target changed after the proposal was created.
- API credentials are loaded from environment variables rather than committed configuration.

AI-generated modifications can still be wrong. Review important changes.

## Planned project structure

```text
pititino/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── pititino/
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── tui/
│       │   ├── app.py
│       │   └── widgets/
│       ├── agent/
│       │   ├── runtime.py
│       │   ├── conversation.py
│       │   └── prompts.py
│       ├── llm/
│       │   └── openai.py
│       ├── tools/
│       │   ├── registry.py
│       │   ├── filesystem.py
│       │   ├── excel.py
│       │   ├── csv.py
│       │   ├── text.py
│       │   ├── json.py
│       │   └── yaml.py
│       └── transactions/
│           ├── backup.py
│           ├── changeset.py
│           └── executor.py
└── tests/
```

## Development

```bash
git clone https://github.com/fjaraya/pititino.git
cd pititino

uv sync --all-groups
```

Run the application:

```bash
uv run pititino
```

Run tests:

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
```

Format:

```bash
uv run ruff format .
```

The current vertical slice includes workspace-safe filesystem tools, bounded XLSX
inspection, native OpenAI tool calling, streamed responses, Textual chat execution,
a dedicated change-plan panel, and approved XLSX change sets with backups and
temporary-file replacement. JSON tool-calling fallback, bounded CSV/text/JSON/YAML
reads, approved text/CSV/JSON/YAML changes, and confirmed backup restore are supported.

## Initial roadmap

### v0.1

- Textual TUI.
- Filesystem browser.
- Interactive chat.
- OpenAI-compatible client configuration.
- Streaming responses.
- Controlled tool registry.
- XLSX inspection.
- XLSX worksheet creation and cell/table writes.
- Text, Markdown, JSON, YAML, and CSV basics.
- Change-plan preview.
- Write confirmation.
- Backups.
- Workspace path restrictions.

### Later

Potential additions include richer spreadsheet formatting, charts and formulas, DOCX and PPTX adapters, PDF inspection, multiple selected files as context, reusable workflows, adapter discovery, session history, model profiles, and richer diff visualizations.

## Non-goals

Pititino is not intended to be:

- a general-purpose shell agent;
- an unrestricted code execution environment;
- a replacement for spreadsheet applications;
- a cloud file-storage service;
- tied to a single AI provider.

Its focus is controlled, AI-assisted manipulation of local files from the terminal.

## Contributing

Pititino is in early development. Issues and pull requests are welcome once the initial implementation is available.

For larger changes, open an issue first so the proposed behavior and tool contract can be discussed before implementation.

## License

Licensed under the **Apache License, Version 2.0**.

See [LICENSE](LICENSE) for the full license text.
