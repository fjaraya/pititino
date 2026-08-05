from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from pititino.config import Settings
from pititino.errors import AgentRuntimeError, ModelEndpointError, PititinoError
from pititino.models.base import ModelBackend
from pititino.tools.registry import ToolRegistry
from pititino.transactions.changeset import ChangeSet

ToolActivity = Callable[[str], Awaitable[None] | None]
TextDelta = Callable[[str], Awaitable[None] | None]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class AssistantResult:
    content: str
    tool_calls: list[ToolCall]


class AgentRuntime:
    """Run a bounded tool-calling conversation through a model backend."""

    def __init__(
        self,
        settings: Settings,
        registry: ToolRegistry,
        client: ModelBackend,
        on_tool_activity: ToolActivity | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry
        self.client = client
        self.on_tool_activity = on_tool_activity
        self.pending_changes: list[ChangeSet] = []
        self.conversation_history: list[dict[str, str]] = []

    def reset_conversation(self) -> None:
        """Clear completed user and assistant turns for the current session."""
        self.conversation_history.clear()

    async def run(
        self,
        user_message: str,
        *,
        selected_file: str | None = None,
        on_text_delta: TextDelta | None = None,
    ) -> str:
        self.pending_changes.clear()
        context = ""
        if selected_file:
            context = f"\nThe user currently selected this workspace file: {selected_file}"
        tools = self._tool_schemas()
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are Pititino, a safe local file workbench. Use the provided typed tools "
                    "to inspect files instead of inventing contents. Inspect before modifying. "
                     "Only claim a tool operation succeeded when its result says it did. "
                     "Keep responses concise and grounded in returned data. "
                     "After each tool result, continue the task until it is complete. "
                     "Never return an empty response: provide the next JSON action or a concise final answer. "
                     "If native tool calls are unavailable, return one JSON action object "
                    "with `action` and `arguments` fields. Available JSON action schemas:\n"
                    + json.dumps(tools, ensure_ascii=True)
                    + context
                ),
            },
            *self.conversation_history,
            {"role": "user", "content": user_message},
        ]
        json_mode = self.settings.model.tool_calling == "json"
        native_tool_calls_seen = False
        tool_calls_executed = False
        empty_response_retries = 0

        for round_number in range(1, self.settings.agent.max_tool_rounds + 1):
            try:
                response = await self._request_with_timeout(
                    messages, tools, on_text_delta, json_mode
                )
            except TimeoutError as exc:
                raise AgentRuntimeError(
                    f"Agent request exceeded timeout ({self.settings.agent.timeout_seconds:g}s)"
                ) from exc
            except ModelEndpointError:
                if self.settings.model.tool_calling != "auto" or json_mode:
                    raise
                json_mode = True
                await self._activity("native tool calling unavailable; using JSON actions")
                response = await self._request_with_timeout(
                    messages, tools, on_text_delta, json_mode
                )
            tool_calls = response.tool_calls
            if (
                not tool_calls
                and self.settings.model.tool_calling == "auto"
                and not json_mode
                and not native_tool_calls_seen
                and not self.conversation_history
                and callable(getattr(self.client, "complete", None))
            ):
                json_mode = True
                await self._activity("native response contained no tool call; using JSON actions")
                response = await self._request_with_timeout(
                    messages, tools, on_text_delta, json_mode
                )
                tool_calls = response.tool_calls
            if not tool_calls:
                if not response.content.strip() and tool_calls_executed and empty_response_retries == 0:
                    empty_response_retries += 1
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Continue the requested task using the tool result above. "
                                "Return the next JSON action if more work is needed, or a concise final answer."
                            ),
                        }
                    )
                    continue
                final_response = response.content or (
                    "The model returned no final response after the tool operation."
                )
                self._remember_turn(user_message, final_response)
                return final_response
            if not json_mode:
                native_tool_calls_seen = True

            if json_mode:
                for call in tool_calls:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "action": call.name,
                                    "arguments": json.loads(call.arguments),
                                },
                                ensure_ascii=True,
                            ),
                        }
                    )
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or None,
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.name,
                                    "arguments": call.arguments,
                                },
                            }
                            for call in tool_calls
                        ],
                    }
                )
            for call in tool_calls:
                name = call.name
                await self._activity(f"calling {name}")
                try:
                    arguments = json.loads(call.arguments)
                    definition = self.registry.get(name)
                    result = self.registry.invoke(name, arguments)
                    if definition.mutating:
                        change = ChangeSet.model_validate(result)
                        self.pending_changes.append(change)
                        await self._activity(f"proposed change: {change.summary}")
                    serializable = result.model_dump() if isinstance(result, BaseModel) else result
                    content = json.dumps(serializable, ensure_ascii=True, default=str)
                except (json.JSONDecodeError, PititinoError, OSError, KeyError) as exc:
                    content = json.dumps({"error": str(exc)})
                await self._activity(f"completed {name}")
                tool_calls_executed = True
                if json_mode:
                    messages.append(
                        {"role": "user", "content": f"Tool result for {name}:\n{content}"}
                    )
                else:
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
        raise AgentRuntimeError(
            f"Agent exceeded max_tool_rounds ({self.settings.agent.max_tool_rounds})"
        )

    def _remember_turn(self, user_message: str, assistant_message: str) -> None:
        self.conversation_history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )
        max_messages = self.settings.agent.max_history_turns * 2
        del self.conversation_history[:-max_messages]

    async def _request_with_timeout(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_text_delta: TextDelta | None,
        json_mode: bool,
    ) -> AssistantResult:
        try:
            return await asyncio.wait_for(
                self._request(messages, tools, on_text_delta, json_mode),
                timeout=self.settings.agent.timeout_seconds,
            )
        except TimeoutError as exc:
            raise AgentRuntimeError(
                f"Agent request exceeded timeout ({self.settings.agent.timeout_seconds:g}s)"
            ) from exc

    async def _request(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_text_delta: TextDelta | None,
        json_mode: bool,
    ) -> AssistantResult:
        if json_mode:
            response = await self.client.complete(messages, [])
            message = response.choices[0].message
            return self._parse_json_action(message.content or "")
        if on_text_delta is None or not hasattr(self.client, "stream"):
            response = await self.client.complete(messages, tools)
            message = response.choices[0].message
            return AssistantResult(
                content=message.content or "",
                tool_calls=[
                    ToolCall(call.id, call.function.name, call.function.arguments)
                    for call in (message.tool_calls or [])
                ],
            )

        stream = await self.client.stream(messages, tools)
        text_parts: list[str] = []
        calls: dict[int, dict[str, str]] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                text_parts.append(delta.content)
                await self._text_delta(on_text_delta, delta.content)
            for tool_delta in delta.tool_calls or []:
                index = tool_delta.index
                call = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                if tool_delta.id:
                    call["id"] = tool_delta.id
                if tool_delta.function:
                    if tool_delta.function.name:
                        call["name"] += tool_delta.function.name
                    if tool_delta.function.arguments:
                        call["arguments"] += tool_delta.function.arguments
        return AssistantResult(
            content="".join(text_parts),
            tool_calls=[ToolCall(call["id"], call["name"], call["arguments"]) for call in calls.values()],
        )

    def _parse_json_action(self, content: str) -> AssistantResult:
        candidate = content.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            lines = candidate.splitlines()
            candidate = "\n".join(lines[1:-1]).strip()
        try:
            action = json.loads(candidate)
        except json.JSONDecodeError:
            return AssistantResult(content=content, tool_calls=[])
        if not isinstance(action, dict) or not isinstance(action.get("action"), str):
            return AssistantResult(content=content, tool_calls=[])
        arguments = action.get("arguments", {})
        return AssistantResult(
            content="",
            tool_calls=[
                ToolCall(
                    id="json-call-1",
                    name=action["action"],
                    arguments=json.dumps(arguments, ensure_ascii=True),
                )
            ],
        )

    def _tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": definition.args_model.model_json_schema(),
                },
            }
            for definition in self.registry.definitions()
        ]

    async def _activity(self, text: str) -> None:
        if self.on_tool_activity is None:
            return
        result = self.on_tool_activity(text)
        if inspect.isawaitable(result):
            await result

    async def _text_delta(self, callback: TextDelta, text: str) -> None:
        result = callback(text)
        if inspect.isawaitable(result):
            await result
