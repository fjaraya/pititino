class PititinoError(Exception):
    """Base class for expected Pititino errors."""


class ConfigurationError(PititinoError):
    """Configuration could not be loaded or validated."""


class WorkspaceAccessError(PititinoError):
    """A path is outside the configured workspace or is otherwise unsafe."""


class ToolValidationError(PititinoError):
    """Tool name or arguments failed validation."""


class ToolExecutionError(PititinoError):
    """A validated tool failed during execution."""


class UnsupportedFileTypeError(PititinoError):
    """The requested adapter does not support the file type."""


class WorkbookReadError(PititinoError):
    """An XLSX workbook could not be inspected or read."""


class ModelEndpointError(PititinoError):
    """The configured model endpoint could not complete a request."""


class AgentRuntimeError(PititinoError):
    """The agent could not safely complete its bounded run."""
