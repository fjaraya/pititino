from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import ClassVar

import pytest

from pititino.agent.pydantic_backend import PydanticAgentBackend
from pititino.config import Settings
from pititino.tools import build_registry
from pititino.workspace import Workspace


class NativeToolHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict]] = []

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        self.__class__.requests.append(request)
        if len(self.requests) == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-list",
                        "type": "function",
                        "function": {
                            "name": "filesystem.list",
                            "arguments": '{"path":"."}',
                        },
                    }
                ],
            }
            finish_reason = "tool_calls"
        else:
            message = {"role": "assistant", "content": "Workspace inspected."}
            finish_reason = "stop"
        body = {
            "id": "chatcmpl-pydantic-test",
            "object": "chat.completion",
            "created": 1,
            "model": request["model"],
            "choices": [{"index": 0, "finish_reason": finish_reason, "message": message}],
        }
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.mark.anyio
async def test_pydantic_backend_runs_native_tool_loop_against_compatible_server(tmp_path) -> None:
    NativeToolHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), NativeToolHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        settings = Settings(
            model={
                "api": "chat_completions",
                "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                "model": "native-test",
                "tool_calling": "native",
            }
        )
        backend = PydanticAgentBackend(settings, build_registry(Workspace(tmp_path), settings))

        result = await backend.run("List the workspace")

        assert result == "Workspace inspected."
        assert len(NativeToolHandler.requests) == 2
        assert NativeToolHandler.requests[0]["tools"]
        assert NativeToolHandler.requests[1]["messages"][-1]["role"] == "tool"
    finally:
        server.shutdown()
        thread.join(timeout=2)
