from pydantic import BaseModel, Field

from pititino.tools.filesystem import ReadTextArguments, read_text
from pititino.transactions.changeset import ChangeOperation, ChangeSet


class ReplaceArguments(BaseModel):
    file: str
    old: str = Field(min_length=1)
    new: str
    count: int = Field(default=-1, ge=-1)


class AppendArguments(BaseModel):
    file: str
    content: str


def propose_replace(arguments: ReplaceArguments) -> ChangeSet:
    return ChangeSet(
        target=arguments.file,
        summary=f"Replace text in {arguments.file}",
        operations=[
            ChangeOperation(
                operation="text_replace",
                description=f"Replace {arguments.old!r} in {arguments.file}",
                arguments=arguments.model_dump(),
            )
        ],
    )


def propose_append(arguments: AppendArguments) -> ChangeSet:
    return ChangeSet(
        target=arguments.file,
        summary=f"Append text to {arguments.file}",
        operations=[
            ChangeOperation(
                operation="text_append",
                description=f"Append content to {arguments.file}",
                arguments=arguments.model_dump(),
            )
        ],
    )

__all__ = [
    "AppendArguments",
    "ReadTextArguments",
    "ReplaceArguments",
    "propose_append",
    "propose_replace",
    "read_text",
]
